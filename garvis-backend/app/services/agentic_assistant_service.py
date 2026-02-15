import app.constants.agentic_assistant_constants as agent_constants
import app.schemas.client_command as client_command
import app.utils.agent_utils as agent_utils
import app.utils.image_utils as image_utils
import app.utils.llm_utils as llm_utils
import base64, mimetypes
import os

from app.core.dto.agent_state import AgentState
from app.core.dto.garvis_dtos import GarvisReply, GarvisTask
from app.database.duckdb_data_service import DataService
from app.utils.agent_utils import AssertImageSent
from fastapi import HTTPException, status
from langgraph.checkpoint.memory import InMemorySaver
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_ollama import ChatOllama
from langchain.tools import InjectedState
from threading import Lock
from typing import ClassVar, Optional, Annotated

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
                    cls._ollama_client_pure_text = llm_utils.instantiate_ollama_llm(
                        model_name=os.getenv("MEDGEMMA_TEXT_ONLY_MODEL_NAME")
                    )
        return cls._ollama_client_pure_text

    @classmethod
    def get_ollama_with_image(cls) -> ChatOllama:
        if cls._ollama_client_with_image is None:
            with cls._ollama_lock:
                if cls._ollama_client_with_image is None:
                    print("Instantiating Vision MedGemma!")
                    cls._ollama_client_with_image = llm_utils.instantiate_ollama_llm(
                        model_name=os.getenv("MEDGEMMA_WITH_IMAGE_MODEL_NAME")
                    )
        return cls._ollama_client_with_image

    @classmethod
    def initialize(cls, data_service: DataService):
        cls._data_service = data_service

    def _initialize_orchestrating_llms(self):
        self._orchetrating_llm_flavor = os.getenv("LLM_FLAVOR")
        if self._orchetrating_llm_flavor == "GOOGLE":
            self._orchestrating_llm_with_tools = llm_utils.instantiate_google_llm(
                model_name=os.getenv("GEMINI_MODEL")
            ).bind_tools(self.return_tools(), strict=True)
            self._llm_with_no_tools = llm_utils.instantiate_google_llm(
                model_name=os.getenv("GEMINI_MODEL")
            )
        else:
            self._orchestrating_llm_with_tools = llm_utils.instantiate_openai_llm(
                model_name=os.getenv("OPENAI_MODEL")
            ).bind_tools(self.return_tools(), strict=True)
            self._llm_with_no_tools = llm_utils.instantiate_openai_llm(
                model_name=os.getenv("OPENAI_MODEL")
            )

    def __init__(self,persist_graph_visualization=False):
        self.ollama_pure_text = AgenticAssistantService.get_ollama_pure_text()
        self.ollama_with_image = AgenticAssistantService.get_ollama_with_image()
        self._graph = None
        self.im_alive = True
        self._initialize_orchestrating_llms()

        if not self._graph:
            self._graph = self._build_graph()

        if persist_graph_visualization:
            png_bytes = self._graph.get_graph().draw_mermaid_png()
            with open("./app/services/graph_visualization/graph.png", "wb") as f:
                f.write(png_bytes)

    def _get_tool_method_call(self):
        return "function_calling" if self._orchetrating_llm_flavor == "GOOGLE" else "json_schema"

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
        df = df.where(df.notna(), "")
        return f"SQL:\n{sql}\n\nResult:\n{df.to_markdown(index=False)}"

    @tool
    def medgemma_reasoner_text(task: str) -> str:
        """
        This is the MEDGEMMA tool for pure text only. Use the Med Gemma model for medical-related inquiries, like asking what disease or ailment shows certain symptoms.
        Or in cases where for certain situations, what is the first aid or certain diseases.
        Only use this if the intent is very clear.
        """
        config = {}

        resp = AgenticAssistantService.get_ollama_pure_text().invoke(
            [
                SystemMessage(content=agent_constants.MEDGEMMA_TEXT_ONLY_MODEL_NAME),
                HumanMessage(content=task),
            ],
            config=config,
        )

        return resp.content

    @tool
    def medgemma_reasoner_image(
        task: str,
        image_b64: Annotated[Optional[str], InjectedState("image_b64")],
        image_mime: Annotated[Optional[str], InjectedState("image_mime")],
    ) -> str:
        """
        This is the MEDGEMMA tool when submitting medical text inquiries with medical images.
        Use the Med Gemma model for medical-related inquiries and when analyzing medical images.
        Examples are like when asking what disease or ailment shows certain symptoms, or summarizing a medical image such as xray, CT-scan in base 64 format.
        Only use this if the intent is very clear and you are certain that the image is medical in nature.
        """
        handler = AssertImageSent(caller="medgemma",raise_if_missing=True)

        content_parts = [{"type": "text", "text": task}]

        if image_b64:
            mime = image_mime or "image/jpeg"
            content_parts.insert(
                0,
                {"type": "image_url", "image_url": f"data:{mime};base64,{image_b64}"},
            )

        resp = AgenticAssistantService.get_ollama_with_image().invoke(
            [
                SystemMessage(content=agent_constants.MEDGEMMA_WITH_IMAGE_MODEL_PROMPT),
                HumanMessage(content=content_parts),
            ],
            config={"callbacks": [handler]},
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

        tools_collection.extend(
            AgenticAssistantService._data_service.return_agent_tools()
        )

        return tools_collection

    def _assistant_node(self, state: AgentState) -> AgentState:
        handler = AssertImageSent(caller="orchestrating_llm",raise_if_missing=True)
        response = self._orchestrating_llm_with_tools.invoke(
            [SystemMessage(content=agent_constants.SYSTEM_PROMPT)] + state["messages"],
            config={"callbacks": [handler]},
        )
        state["messages"] = state["messages"] + [response]
        return state

    def _clean_up_images(self, state: AgentState) -> AgentState:
        state["image_b64"] = None
        state["image_b64_lower_quality"] = None
        state["image_mime"] = None
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

    def _build_graph(self):
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
        builder.add_node("clean_up_images", self._clean_up_images)
        builder.add_edge("route_to_client_command", "clean_up_images")
        builder.add_edge("clean_up_images", END)

        compiled_graph = builder.compile(checkpointer=checkpointer)

        return compiled_graph

    def _chat(
        self,
        user_text: str,
        image_path: Optional[str] = None,
        thread_id: str = "demo",
        display_tool_call: bool = True,
        image_b64: Optional[str] = None,
    ) -> str:
        try:
            image_mime = None
            cfg = {"configurable": {"thread_id": thread_id}}

            blocks = []
            if user_text.strip():
                blocks.append({"type": "text", "text": user_text.strip()})

            if image_b64:
                validation_check = image_utils.detect_image_mime_pillow(image_b64)

                if not validation_check["is_image"]:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="base64 string is not an image, incomplete, or corrupted",
                    )
                else:
                    image_mime = validation_check["mime"]

                squared_image = image_utils.image_dimensions_to_square(image_b64)
                resized_and_lower_quality = image_utils.decrease_image_size(squared_image)
                blocks.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{image_mime};base64,{resized_and_lower_quality}"
                        },
                    }
                )

            if image_path:
                image_mime, _ = mimetypes.guess_type(image_path)

                with open(image_path, "rb") as f:
                    raw_bytes = f.read()

                if (
                    image_mime in ("image/tiff", "image/x-tiff")
                ) or image_path.lower().endswith((".tif", ".tiff")):
                    jpeg_bytes = image_utils.tiff_bytes_to_jpeg_bytes(raw_bytes)
                    image_b64 = base64.b64encode(jpeg_bytes).decode("utf-8")
                    image_mime = "image/jpeg"
                elif image_mime in ("image/png"):
                    image_b64 = image_utils.png_b64_to_jpg_b64_no_alpha(raw_bytes)
                    image_mime = "image/jpeg"
                elif image_mime in ("image/jpg","image/jpeg","image/jpe"):
                    image_b64 = base64.b64encode(raw_bytes)
                    image_mime = "image/jpeg"
                elif image_mime in ("image/bmp","image/x-ms-bmp"):
                    image_b64 = image_utils.bmp_b64_to_jpg_b64(raw_bytes)
                    image_mime = "image/jpeg"
                else:
                    image_b64 = base64.b64encode(raw_bytes)
                    image_mime = image_mime or "image/jpeg"                    

                squared_image = image_utils.image_dimensions_to_square(image_b64)
                resized_and_lower_quality = image_utils.decrease_image_size(squared_image)
                blocks.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{image_mime};base64,{resized_and_lower_quality}"
                        },
                    }
                )

            # the trick here is that when passing to the main orchestrating LLM, we use a lower quality and lower resolution
            # but we will pass the squared_image version of the high quality image to the medgemma LLM
            init_state = {
                "messages": [HumanMessage(content=blocks if blocks else user_text)],
                "image_b64": squared_image if image_b64 else None,
                "image_mime": image_mime if image_mime else None,
                "parameters": {"id": "id"},
            }

            final_state = self._graph.invoke(init_state, config=cfg)

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
                if self._orchetrating_llm_flavor == "GOOGLE"
                else final_state["messages"][-1].content
            )

            return (
                content,
                final_state["view"],
                final_state["action"],
                final_state["parameters"],
                final_state["intent_confidence"],
            )
        except Exception as ex:
            print(ex)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"sorry, error",
            )

    def call_agent(self, garvis_task: GarvisTask) -> GarvisReply:

        content, view, action, parameters, intent_confidence = self._chat(
            user_text=garvis_task.query,
            image_path=garvis_task.uploaded_file_path,
            thread_id=garvis_task.session_id,
            display_tool_call=True,
            image_b64=garvis_task.base64_image,
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
