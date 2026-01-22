#React = reasoning and acting

import os
from typing import Annotated, Sequence, TypedDict
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage #foundational class for all message types in LangGraph
from langchain_core.messages import ToolMessage #passes data back to LLM after it calls a tool
from langchain_core.messages import SystemMessage #Message for providing instructions to the LLM
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph.message import add_messages #a reducer function, a way to append and preserve messages of sorts
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

load_dotenv()

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

@tool
def add(a:int, b:int):
    #docstring is ESSENTIAL, it tells the LLM what the tool is for
    """This is a function that adds two numbers and return the sum"""
    return a+b

@tool
def subtract(a:int, b:int):
    #docstring is ESSENTIAL, it tells the LLM what the tool is for
    """This is a function that subtracts two numbers and return the sum"""
    return a-b

@tool
def multiply(a:int, b:int):
    #docstring is ESSENTIAL, it tells the LLM what the tool is for
    """This is a function that multiplies two numbers and return the sum"""
    return a*b

@tool
def divide(a:int, b:int):
    #docstring is ESSENTIAL, it tells the LLM what the tool is for
    """This is a function that divides two numbers and return the sum"""
    return a/b

tools = [add, subtract, multiply, divide]

llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL")).bind_tools(tools)

def model_call(state: AgentState) -> AgentState:
    system_prompt = SystemMessage(content = "You are my AI assistant, please answer my query to the best of your ability.")
    response = llm.invoke([system_prompt] + state["messages"])
    return {"messages":[response]} #add_messages REDUCER function automatically handles appending of response 

def should_continue(state: AgentState) -> AgentState:
    messages = state["messages"]
    last_message = messages[-1]

    if(not last_message.tool_calls):
        return "end"
    else:
        return "continue"

graph = StateGraph(AgentState)
graph.add_node("our_agent",model_call)

tool_node = ToolNode(tools=tools)
graph.add_node("tools",tool_node)

graph.add_edge(START, "our_agent")

graph.add_conditional_edges(
    "our_agent"
    , should_continue
    ,{
        "continue":"tools"
        , "end":END
    }
)

graph.add_edge("tools", "our_agent")

app = graph.compile()

def print_stream(stream):
    for s in stream:
        message = s["messages"][-1]
        if(isinstance(message, tuple)):
            print(message)
        else:
            message.pretty_print()

#inputs = {"messages":[("user","Add the first pair which 3 and 4, then add the second pair 5 and 7, then finally add 100 and the sum of the second pair of numbers")]}
#print_stream(app.stream(inputs, stream_mode="values"))


inputs = {"messages":[("user","Add 40 and 12, then multiply the output by 6. Then finally, subtract 20. Then write the final value in roman numeric value")]}
print_stream(app.stream(inputs, stream_mode="values"))