import duckdb
import os
import re

from dotenv import load_dotenv
from langgraph.checkpoint.memory import InMemorySaver
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from typing import ClassVar, Optional

from app.core.dto.agent_state import AgentState
from app.core.dto.garvis_task import GarvisTask
from app.core.dto.garvis_reply import GarvisReply
import app.constants.agentic_assistant as agent_constants

from threading import Lock
from app.database.duckdb_data_service import DataService
from app.schemas.client_command import ClientCommand


class AgenticAssistantService:
    OLLAMA_MODEL: ClassVar[str] = "MedAIBase/MedGemma1.5:4b"
    _ollama_lock: ClassVar[Lock] = Lock()
    _ollama_client: ClassVar[Optional[ChatOllama]] = None
    _data_service: DataService = None

    @classmethod
    def get_ollama(cls) -> ChatOllama:
        # Double-checked locking
        if cls._ollama_client is None:
            with cls._ollama_lock:
                if cls._ollama_client is None:
                    print("instantiating ollama!")
                    cls._ollama_client = ChatOllama(
                        model=cls.OLLAMA_MODEL,
                        temperature=0,
                    )
        return cls._ollama_client

    @classmethod
    def initialize(cls, data_service: DataService):
        cls._data_service = data_service

    def _load_env(self):
        load_dotenv()

    def __init__(self):
        self.llm_ollama = AgenticAssistantService.get_ollama()
        self.llm_openai = None
        self.graph = None

        self._load_env()
        self.im_alive = True
        self.llm_openai = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL")
            , temperature=0
        ).bind_tools(self.return_tools())

        if(not self.graph):
            self.graph = self.build_graph()

    def route_to_client_command(self, state: AgentState) -> AgentState:
        # You can pass full history, or truncate to last N messages for cost control
        #messages = state.get("messages", [])
        #last_messages = messages[-4:]  # <-- only last 4
        last_messages = state.get("messages", [])

        router = self.llm_openai.with_structured_output(ClientCommand)
        reply = router.invoke(
            [{"role": "system", "content": agent_constants.ROUTER_SYSTEM_PROMPT}, *last_messages]
        )

        state["view"] = reply.view
        state["action"] = reply.action
        state["parameters"] = reply.parameters
        state["intent_confidence"] = reply.intent_confidence
        state["reasoning_short"] = reply.reasoning_short

        # Return only the state updates you want to apply
        return state
    
    
    def _sanitize_sql(sql: str) -> str:

        _SQL_DISALLOWED = re.compile(agent_constants.DISALLOWED_SQL,re.IGNORECASE)

        sql = (sql or "").strip().strip("`")
        sql = re.sub(r"^```(sql)?\s*|\s*```$", "", sql, flags=re.IGNORECASE).strip()

        # block multi-statements
        if ";" in sql:
            raise ValueError("Only a single SQL statement is allowed (no semicolons).")

        if _SQL_DISALLOWED.search(sql):
            raise ValueError("Only read-only queries are allowed (SELECT / WITH).")

        if not re.match(r"^(SELECT|WITH)\b", sql, flags=re.IGNORECASE):
            raise ValueError("Query must start with SELECT or WITH.")

        # keep results manageable
        if not re.search(r"\bLIMIT\b", sql, flags=re.IGNORECASE):
            sql = f"{sql}\nLIMIT 200"
        return sql

    def _schema_markdown(conn: duckdb.DuckDBPyConnection) -> str:
        tables = [r[0] for r in conn.execute("SHOW TABLES").fetchall()]
        if not tables:
            return "(no tables found)"
        out = []
        for t in tables:
            cols = conn.execute(f"DESCRIBE {t}").fetchall()
            out.append(f"### {t}")
            for c in cols:
                out.append(f"- {c[0]}: {c[1]}")
            out.append("")
        return "\n".join(out).strip()

    @tool
    def get_schema() -> str:
        """Return the DuckDB schema information (tables and columns) in a compact format."""

        with AgenticAssistantService._data_service.connection() as con:
            database_markdown = AgenticAssistantService._schema_markdown(con)

        return database_markdown

    @tool
    def run_sql(query: str) -> str:
        """
        Execute a read-only SQL query (SELECT/WITH) against DuckDB and return results as markdown.
        """
        sql = AgenticAssistantService._sanitize_sql(query)

        with AgenticAssistantService._data_service.connection() as con:
            df = con.execute(sql).df()

        if df.empty:
            return f"SQL:\n{sql}\n\nResult: (no rows)"
        return f"SQL:\n{sql}\n\nResult:\n{df.to_markdown(index=False)}"

    @tool
    def medgemma_reasoner(task: str) -> str:
        """
        Use the Med Gemma model for medical-related inquiries, like asking what disease or ailment shows certain symptoms.
        Or in cases where for certain situations, what is the first aid
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

        tools_collection.extend(AgenticAssistantService._data_service.export_tools())

        return tools_collection

    def assistant_node(self, state: AgentState) -> AgentState:
        response = self.llm_openai.invoke(
            [SystemMessage(content=agent_constants.SYSTEM_PROMPT)] + state["messages"]
        )
        state["messages"] = state["messages"] + [response]
        return state

    def should_continue(self, state: AgentState) -> str:
        state_messages = state[
            "messages"
        ]  # copies the latest state into the "messages" variable
        last_message = state_messages[-1]  # get only the last message

        if not last_message.tool_calls:
            return "route_to_client_command"
        else:
            return "tools"

    def build_graph(self):
        checkpointer = InMemorySaver()
        builder = StateGraph(AgentState)
        builder.add_node("assistant", self.assistant_node)
        builder.add_node("tools", ToolNode(self.return_tools()))
        builder.add_edge(START, "assistant")
        builder.add_conditional_edges(
            "assistant", self.should_continue, {"tools": "tools", "route_to_client_command": "route_to_client_command"}
        )
        builder.add_edge("tools", "assistant")
        builder.add_node("route_to_client_command",self.route_to_client_command)
        builder.add_edge("route_to_client_command", END)

        return builder.compile(checkpointer=checkpointer)   

    def _chat(
        self, user_text: str, thread_id: str = "demo", display_tool_call: bool = True
    ) -> str:
        cfg = {"configurable": {"thread_id": thread_id}}
        final_state = self.graph.invoke(
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
                , final_state['parameters']

    def call_agent(self, garvis_task: GarvisTask):
        content, view, action, parameters = self._chat(
            user_text=garvis_task.query,
            thread_id=garvis_task.session_id,
            display_tool_call=False,
        )
        print(content, view, action, parameters)
        return GarvisReply(garvis_task.session_id
                           , garvis_task.query
                           , content
                           , view
                           , action
                           , parameters)