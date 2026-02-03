import app.constants.agentic_assistant_constants as agent_constants
import app.utils.agent_utils as agent_utils
import os

from app.core.dto.agent_state import AgentState
from app.core.dto.garvis_dtos import GarvisReply, GarvisTask
from app.database.duckdb_data_service import DataService
from app.schemas.client_command import ClientCommand

from langgraph.checkpoint.memory import InMemorySaver
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_google_genai import ChatGoogleGenerativeAI #will try soon :)
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from threading import Lock
from typing import ClassVar, Optional

class AgenticAssistantService:
    _ollama_lock: ClassVar[Lock] = Lock()
    _ollama_client: ClassVar[Optional[ChatOllama]] = None
    _data_service: DataService = None

    @classmethod
    def get_ollama(cls) -> ChatOllama:
        if cls._ollama_client is None:
            with cls._ollama_lock:
                if cls._ollama_client is None:
                    print("instantiating ollama!")
                    cls._ollama_client = ChatOllama(
                        model=agent_constants.MEDGEMMA_MODEL_NAME,
                        temperature=0,
                    )
        return cls._ollama_client

    @classmethod
    def initialize(cls, data_service: DataService):
        cls._data_service = data_service

    def _initialize_orchestrating_llm(self):
        self._llm_flavor = os.getenv("LLM_FLAVOR")
        print(self._llm_flavor)
        if(os.getenv("LLM_FLAVOR") == "GOOGLE"):
            self._orchestrating_llm_with_tools =  ChatGoogleGenerativeAI(model=os.getenv("GEMINI_MODEL"),temperature=0,timeout=120,max_retries=2).bind_tools(self.return_tools())
            self._llm_with_no_tools = ChatGoogleGenerativeAI(model=os.getenv("GEMINI_MODEL"),temperature=0,timeout=120,max_retries=2)
        else:
            self._orchestrating_llm_with_tools = ChatOpenAI(model=os.getenv("OPENAI_MODEL"), temperature=0,timeout=120).bind_tools(self.return_tools())
            self._llm_with_no_tools = ChatOpenAI(model=os.getenv("OPENAI_MODEL"), temperature=0,timeout=120)

    def __init__(self):
        self.llm_ollama = AgenticAssistantService.get_ollama()
        self._graph = None
        self.im_alive = True
        self._initialize_orchestrating_llm()

        if(not self._graph):
            self._graph = self._build_graph()
 
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
    def medgemma_reasoner(task: str) -> str:
        """
        Use the Med Gemma model for medical-related inquiries, like asking what disease or ailment shows certain symptoms.
        Or in cases where for certain situations, what is the first aid or certain diseases. 
        """

        resp = AgenticAssistantService.get_ollama().invoke(
            [
                SystemMessage(
                    content=agent_constants.MEDGEMMA_SYSEM_PROMPT
                ),
                HumanMessage(content=task),
            ]
        )

        return resp.content

    def return_tools(self):
        tools_collection =  [
            self.get_schema,
            self.run_sql,
            self.medgemma_reasoner,
            DuckDuckGoSearchRun(),
        ]

        tools_collection.extend(AgenticAssistantService._data_service.return_tools())

        return tools_collection

    def _assistant_node(self, state: AgentState) -> AgentState:
        response = self._orchestrating_llm_with_tools.invoke(
            [SystemMessage(content=agent_constants.SYSTEM_PROMPT)] + state["messages"]
        )
        print(response)
        state["messages"] = state["messages"] + [response]
        return state

    def _should_continue(self, state: AgentState) -> str:
        state_messages = state["messages"]  # copies the latest state into the "messages" variable
        last_message = state_messages[-1]  # get only the last message
 
        if not last_message.tool_calls:
            return "route_to_client_command"
        else:
            return "tools"

    def _route_to_client_command(self, state: AgentState) -> AgentState:
        # You can pass full history, or truncate to last N messages for cost control
        #messages = state.get("messages", [])
        #last_n_messages = len(messages) if len(messages) < 4 else 4
        #last_messages = messages[-last_n_messages:]  # <-- only last 4
        
        last_messages = state.get("messages", [])

        router = self._llm_with_no_tools.with_structured_output(ClientCommand)
        reply = router.invoke(
            [{"role": "system", "content": agent_constants.ROUTER_SYSTEM_PROMPT}, *last_messages]
        )

        state["view"] = reply.view
        state["action"] = reply.action
        state["parameters"] = reply.parameters
        state["intent_confidence"] = reply.intent_confidence
        state["reasoning_short"] = reply.reasoning_short
        state["intent_confidence"] = reply.intent_confidence

        # Return only the state updates you want to apply
        return state

    def _build_graph(self):
        checkpointer = InMemorySaver()
        builder = StateGraph(AgentState)
        builder.add_node("assistant", self._assistant_node)
        builder.add_node("tools", ToolNode(self.return_tools()))
        builder.add_edge(START, "assistant")
        builder.add_conditional_edges(
            "assistant", self._should_continue, {"tools": "tools", "route_to_client_command": "route_to_client_command"}
        )
        builder.add_edge("tools", "assistant")
        builder.add_node("route_to_client_command",self._route_to_client_command)
        builder.add_edge("route_to_client_command", END)

        return builder.compile(checkpointer=checkpointer)   

    def _chat(
        self, user_text: str, thread_id: str = "demo", display_tool_call: bool = True
    ) -> str:
        cfg = {"configurable": {"thread_id": thread_id}}
        final_state = self._graph.invoke(
            {"messages": [HumanMessage(content=user_text)],"parameters":{"id":"id"}}, config=cfg
        )

        if display_tool_call:
            for msg in final_state["messages"]:
                if hasattr(msg, "tool_calls"):
                    for index, tool_call in enumerate(msg.tool_calls):
                        print("*" * 100)
                        print(
                            f"Tool Call: #{index+1}| Name: {tool_call["name"]}| Args: {tool_call["args"]}"
                        )

        # The latest assistant message is at the end
        return final_state["messages"][-1].content \
                , final_state['view'] \
                , final_state['action'] \
                , final_state['parameters'] \
                , final_state['intent_confidence']

    def call_agent(self, garvis_task: GarvisTask)->GarvisReply:

        content, view, action, parameters, intent_confidence = self._chat(
            user_text=garvis_task.query,
            thread_id=garvis_task.session_id,
            display_tool_call=False,
        )

        return GarvisReply(garvis_task.session_id
                           , garvis_task.query
                           , content
                           , view
                           , action
                           , parameters
                           , intent_confidence)