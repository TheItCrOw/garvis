from typing import TypedDict, List
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv
import os

load_dotenv()

class AgentState(TypedDict):
    messages: List[HumanMessage]

llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL"))

def process(state: AgentState) -> AgentState:
    response = llm.invoke(state["messages"])
    print(response.content)
    return state

graph = StateGraph(AgentState)
graph.add_node("process",process)
graph.add_edge(START,"process")
graph.add_edge("process",END)
agent = graph.compile()
user_input = input("Enter: ")
while (user_input != "exit"):
    user_response = agent.invoke({"messages":[HumanMessage(content=user_input)]})
    user_input = input("Enter: ")