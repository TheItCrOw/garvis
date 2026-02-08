import app.constants.agentic_assistant_constants as agent_constants
import app.schemas.client_command as client_command
import app.utils.agent_utils as agent_utils
import base64, mimetypes
import os

from app.core.dto.agent_state import AgentState
from app.core.dto.garvis_dtos import GarvisReply, GarvisTask
from app.database.duckdb_data_service import DataService

from langgraph.checkpoint.memory import InMemorySaver
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain.tools import InjectedState  # per docs
from threading import Lock
from typing import ClassVar, Optional, Annotated


#==================

import hashlib
from langchain_core.callbacks import BaseCallbackHandler

def iter_image_urls(content):
    # Handles common multimodal shapes
    if isinstance(content, list):
        for part in content:
            if not isinstance(part, dict):
                continue
            t = part.get("type")
            if t in ("image_url", "input_image"):
                image_url = part.get("image_url")
                if isinstance(image_url, dict):
                    yield image_url.get("url")
                elif isinstance(image_url, str):
                    yield image_url

class AssertImageSent(BaseCallbackHandler):
    def __init__(self, *, raise_if_missing: bool = True):
        self.raise_if_missing = raise_if_missing

    def on_chat_model_start(self, serialized, messages, **kwargs):
        # messages is typically List[List[BaseMessage]] (batched)
        found = False
        for batch in messages:
            for msg in batch:
                for url in iter_image_urls(getattr(msg, "content", None)):
                    if isinstance(url, str) and "base64," in url:
                        b64 = url.split("base64,", 1)[1]
                        h = hashlib.sha256(b64.encode("utf-8")).hexdigest()[:12]
                        print(f"[probe] image data url detected, sha256[:12]={h}, b64_len={len(b64)}")
                        found = True

        if self.raise_if_missing and not found:
            raise RuntimeError("No base64 image block found in LLM input messages.")

#==================

class AgenticAssistantService:
    _ollama_lock: ClassVar[Lock] = Lock()
    _ollama_client_pure_text: ClassVar[Optional[ChatOllama]] = None
    _ollama_client_with_image: ClassVar[Optional[ChatOllama]] = None
    _data_service: DataService = None

    @classmethod
    def get_ollama_pure_text(cls) -> ChatOllama:
        if cls._ollama_client_pure_text is None:
            with cls._ollama_lock:
                if cls._ollama_client_pure_text is None:
                    print("Instantiating Text MedGemma!")
                    cls._ollama_client_pure_text = ChatOllama(
                        model=os.getenv("MEDGEMMA_TEXT_ONLY_MODEL_NAME"),
                        temperature=0,
                    )
        return cls._ollama_client_with_image

    @classmethod
    def get_ollama_with_image(cls) -> ChatOllama:
        if cls._ollama_client_with_image is None:
            with cls._ollama_lock:
                if cls._ollama_client_with_image is None:
                    print("Instantiating Vision MedGemma!")
                    cls._ollama_client_with_image = ChatOllama(
                        model=os.getenv("MEDGEMMA_WITH_IMAGE_MODEL_NAME"),
                        temperature=0,
                    )
        return cls._ollama_client_with_image

    @classmethod
    def initialize(cls, data_service: DataService):
        cls._data_service = data_service

    def _initialize_orchestrating_llms(self):
        self._llm_flavor = os.getenv("LLM_FLAVOR")
        if self._llm_flavor == "GOOGLE":
            self._orchestrating_llm_with_tools = ChatGoogleGenerativeAI(
                model=os.getenv("GEMINI_MODEL"),
                temperature=0,
                timeout=120,
                max_retries=2,
            ).bind_tools(self.return_tools(), strict=True)
            self._llm_with_no_tools = ChatGoogleGenerativeAI(
                model=os.getenv("GEMINI_MODEL"),
                temperature=0,
                timeout=120,
                max_retries=2,
            )
        else:
            self._orchestrating_llm_with_tools = ChatOpenAI(
                model=os.getenv("OPENAI_MODEL"),
                temperature=0,
                timeout=120,
                max_retries=2,
            ).bind_tools(self.return_tools(), strict=True)
            self._llm_with_no_tools = ChatOpenAI(
                model=os.getenv("OPENAI_MODEL"),
                temperature=0,
                timeout=120,
                max_retries=2,
            )

    def __init__(self):
        self.ollama_pure_text = AgenticAssistantService.get_ollama_pure_text()
        self.ollama_with_image = AgenticAssistantService.get_ollama_with_image()
        self._graph = None
        self.im_alive = True
        self._initialize_orchestrating_llms()

        if not self._graph:
            self._graph = self._build_graph()

    def _get_tool_method_call(self):
        return "function_calling" if self._llm_flavor == "GOOGLE" else "json_schema"

    @tool
    def get_schema() -> str:
        """Return the DuckDB schema information (tables and columns) in a compact format."""

        with AgenticAssistantService._data_service.connection() as con:
            database_markdown = agent_utils.schema_markdown(con)

        return database_markdown

    @tool
    def run_sql(query: str) -> str:
        """
        Execute a read-only SQL query (SELECT/WITH) against DuckDB and return results as markdown.
        """
        sql = agent_utils.sanitize_sql(query)

        with AgenticAssistantService._data_service.connection() as con:
            df = con.execute(sql).df()

        if df.empty:
            return f"SQL:\n{sql}\n\nResult: (no rows)"
        return f"SQL:\n{sql}\n\nResult:\n{df.to_markdown(index=False)}"

    @tool
    def medgemma_reasoner_text(task: str) -> str:
        """
        This is the MEDGEMMA tool for pure text only. Use the Med Gemma model for medical-related inquiries, like asking what disease or ailment shows certain symptoms, or summarizing a medical image such as xray, CT-scan.
        Or in cases where for certain situations, what is the first aid or certain diseases. Occasionally, you will also get medical images 
        in base 64 format.
        """
        config={}

        resp = AgenticAssistantService.get_ollama_pure_text().invoke(
            [
                SystemMessage(content=agent_constants.MEDGEMMA_TEXT_ONLY_MODEL_NAME),
                HumanMessage(content=task),
            ]
            , config=config
        )

        return resp.content
    
    @tool
    def medgemma_reasoner_image(
        task: str,
        image_b64: Annotated[Optional[str], InjectedState("image_b64")],
        image_mime: Annotated[Optional[str], InjectedState("image_mime")],
    ) -> str:
        """
        This is the MEDGEMMA tool when submitting text with images. Use the Med Gemma model for medical-related inquiries and when analyzing medical images. Examples are like when asking what disease or ailment shows certain symptoms, or summarizing a medical image such as xray, CT-scan.
        Or in cases where for certain situations, what is the first aid or certain diseases.
        in base 64 format.
        """        
        #handler = AssertImageSent(raise_if_missing=True)

        content_parts = [{"type": "text", "text": task}]

        if(image_b64):
            mime = image_mime or "image/jpeg"
            content_parts.insert(
                0,
                {"type": "image_url", "image_url": f"data:{mime};base64,{image_b64}"},
            )

        resp = AgenticAssistantService.get_ollama_with_image() .invoke(
            [
                SystemMessage(content=agent_constants.MEDGEMMA_WITH_IMAGE_MODEL_PROMPT),
                HumanMessage(content=content_parts),
            ],
            #config={"callbacks": [handler]},
        )
        return resp.content

    def return_tools(self):
        tools_collection = [
            self.get_schema,
            self.run_sql,
            self.medgemma_reasoner_text,
            self.medgemma_reasoner_image,
            DuckDuckGoSearchRun(),
        ]

        tools_collection.extend(AgenticAssistantService._data_service.return_tools())

        return tools_collection

    def _assistant_node(self, state: AgentState) -> AgentState:
        response = self._orchestrating_llm_with_tools.invoke(
            [SystemMessage(content=agent_constants.SYSTEM_PROMPT)] + state["messages"]
        )
        state["messages"] = state["messages"] + [response]
        return state

    def _should_continue(self, state: AgentState) -> str:
        state_messages = state[
            "messages"
        ]  # copies the latest state into the "messages" variable
        last_message = state_messages[-1]  # get only the last message

        if not last_message.tool_calls:
            return "route_to_client_command"
        else:
            return "tools"

    def _route_to_client_command(self, state: AgentState) -> AgentState:
        last_messages = state.get("messages", [])

        router = self._llm_with_no_tools.with_structured_output(
            client_command.CLIENT_COMMAND_RAW_SCHEMA,
            method=self._get_tool_method_call(),
        )

        reply = router.invoke(
            [
                {"role": "system", "content": agent_constants.ROUTER_SYSTEM_PROMPT},
                *last_messages,
            ]
        )

        state["view"] = reply["view"]
        state["action"] = reply["action"]
        state["parameters"] = reply["parameters"]
        state["intent_confidence"] = reply["intent_confidence"]
        state["reasoning_short"] = reply["reasoning_short"]

        # Return only the state updates you want to apply
        return state

    def _build_graph(self, persist_graph_visualization=False):
        checkpointer = InMemorySaver()
        builder = StateGraph(AgentState)
        builder.add_node("assistant", self._assistant_node)
        builder.add_node("tools", ToolNode(self.return_tools()))
        builder.add_edge(START, "assistant")
        builder.add_conditional_edges(
            "assistant",
            self._should_continue,
            {"tools": "tools", "route_to_client_command": "route_to_client_command"},
        )
        builder.add_edge("tools", "assistant")
        builder.add_node("route_to_client_command", self._route_to_client_command)
        builder.add_edge("route_to_client_command", END)

        compiled_graph =  builder.compile(checkpointer=checkpointer)
        
        if(persist_graph_visualization):
            png_bytes = compiled_graph.get_graph().draw_mermaid_png()
            with open("./app/services/graph_visualization/graph.png", "wb") as f:
                f.write(png_bytes)

        return compiled_graph

    def _chat(
        self, user_text: str
        , image_path: Optional[str] = None
        , thread_id: str = "demo"
        , display_tool_call: bool = True
    ) -> str:
        
        image_b64 = None
        image_mime = None
        cfg = {"configurable": {"thread_id": thread_id}}

        blocks = []
        if(user_text.strip()):
            blocks.append({"type": "text", "text": user_text.strip()})

        if image_path:
            image_mime, _ = mimetypes.guess_type(image_path)
            image_mime = image_mime or "image/jpeg"
            with open(image_path, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode("utf-8")

            blocks.append({"type": "image_url", "image_url": {"url": f"data:{image_mime};base64,{image_b64}"}})

        init_state = {
            "messages": [HumanMessage(content=blocks if blocks else user_text)],
            "image_b64": image_b64 if image_b64 else None,
            "image_mime": image_mime if image_mime else None,
            "parameters": {"id": "id"},
        }

        final_state = self._graph.invoke(init_state,config=cfg)

        if display_tool_call:
            for msg in final_state["messages"]:
                if hasattr(msg, "tool_calls"):
                    for index, tool_call in enumerate(msg.tool_calls):
                        print("*" * 100)
                        print(
                            f"Tool Call: #{index+1}| Name: {tool_call["name"]}| Args: {tool_call["args"]}"
                        )

        # google llms wrap their messages in a list of dicts with a "text" key
        content = (
            final_state["messages"][-1].content[-1]["text"]
            if self._llm_flavor == "GOOGLE"
            else final_state["messages"][-1].content
        )

        return (
            content,
            final_state["view"],
            final_state["action"],
            final_state["parameters"],
            final_state["intent_confidence"],
        )

    def call_agent(self, garvis_task: GarvisTask) -> GarvisReply:

        content, view, action, parameters, intent_confidence = self._chat(
            user_text=garvis_task.query,
            image_path=garvis_task.uploaded_file_path,
            thread_id=garvis_task.session_id,
            display_tool_call=True,
        )

        return GarvisReply(
            garvis_task.session_id,
            garvis_task.query,
            content,
            view,
            action,
            parameters,
            intent_confidence,
        )
