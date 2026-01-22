from typing import TypedDict, List, Union
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv
import os

load_dotenv()

class AgentState(TypedDict):
    messages: List[Union[HumanMessage, AIMessage]]

llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL"))

def process(state: AgentState) -> AgentState:
    """This node will solve the request you input"""
    response = llm.invoke(state["messages"])

    #wrap the content into an AI Message
    state["messages"].append(AIMessage(content=response.content))
    print("*" * 100)
    #print(f"CURRENT STATE: {state['messages']}")
    print(response.content)
    return state

graph = StateGraph(AgentState)
graph.add_node("process",process)
graph.add_edge(START,"process")
graph.add_edge("process",END)
agent = graph.compile()
user_input = input("Enter: ")

conversation_history = []

while (user_input != "exit"):
    conversation_history.append(HumanMessage(content=user_input))
    result = agent.invoke({"messages":conversation_history})

    conversation_history = result["messages"]
    user_input = input("Enter: ")

with open("./logs/02_memory_agent.txt","w") as file:
    file.write("Your Conversation Log:\n")

    for message in conversation_history:
        if(isinstance(message, HumanMessage)):
            file.write(f"You: {message.content}\n")
        elif(isinstance(message, AIMessage)):
            file.write(f"AI: {message.content}\n\n")
    file.write("End of Conversation")

print("Conversation saved to logging.txt")