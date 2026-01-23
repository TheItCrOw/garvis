import os
from typing import Annotated, Sequence, TypedDict
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

load_dotenv()

#global variable to store document content, but the proper way really is to use INJECTED STATE
document_content=""

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

@tool #decorator
def update(content: str)->str: #the LLM will look and parse the definition and parameters of the tool
    """Updates the document with the provided content."""
    global document_content
    template = "Document has been successfully updated! The current content is: ```{document_content}```"
    document_content = content

    return template.format(document_content=document_content)

@tool #decorator
def save(filename: str)->str:
    """
    Save the current document to a text file and finish the process.
    
    Args:
        filename: Name for the text file containing the document content.
    """

    global document_content

    if(not filename.lower().endswith(".txt")):
        filename = f"{filename}.txt"

    try:
        with open(f"./logs/{filename}", "w") as file:
            file.write(document_content)
        print(f"\nDocument has been saved to './logs/{filename}'")
        return f"\nDocument has been saved to './logs/{filename}'"
    except Exception as e:
        return f"Error saving document: {str(e)}"
    
tools = [update, save]

llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL")).bind_tools(tools)

def our_agent(state:AgentState)->AgentState:
    system_prompt_content = f"""
    You are a professional Drafter, a helpful writing assistant. You are going to help the user update and modify documents.
    
    - If the user wants to update or modify content, use the 'update' tool with the complete updated content.
    - If the user wants to save and finish, you need to use the 'save' tool
    - Make sure to always shwo the current document state after modifications.

    The current document content is : '{document_content}'
    """

    system_prompt = SystemMessage(content=system_prompt_content)

    if(not state["messages"]):
        user_input = "I'm ready tp help you update a document. What would you like to create?"
        user_message = HumanMessage(content=user_input)
    else:
        user_input = input("\nWhat would you like to do with the document?")
        print(f"\nUSER:{user_input}")
        user_message = HumanMessage(content=user_input)       

    all_messages = [system_prompt] + list(state["messages"]) + [user_message]

    response = llm.invoke(all_messages)

    print(f"\nAI:{response.content}")

    if(hasattr(response, "tool_calls")) and response.tool_calls:
        print(f"USING TOOLS: {[x["name"] for x in response.tool_calls]}")

    return {"messages":list(state["messages"]) + [user_message, response]}

#====================================================================
def should_continue(state: AgentState) -> str:
    """Determine if we should continue or end the conversation."""

    messages = state["messages"]

    if(not messages):
        return "continue"

    for message in reversed(messages):
        if(isinstance(message,ToolMessage) 
            and "saved" in message.content.lower()
            and "document" in message.content.lower()):
            return "end"

    return "continue"

#====================================================================
def print_messages(messages):
    """Function I made to prin the message in a more readable format"""

    if(not messages):
        return
    
    for message in messages[-3:]:
        if(isinstance(message, ToolMessage)):
            print(f"\nTool Result: {message.content}")

graph = StateGraph(AgentState)
graph.add_node("our_agent",our_agent)
tool_node = ToolNode(tools=tools)
graph.add_node("tools",tool_node)
graph.add_edge(START, "our_agent")
graph.add_edge("our_agent", "tools")

graph.add_conditional_edges(
    "tools"
    , should_continue
    ,{
        "continue":"our_agent"
        , "end":END
    }
)

graph.add_edge("tools", END)
app = graph.compile()

def run_document_agent():
    print("======= DRAFTER =======")

    state = {"messages":[]}

    for step in app.stream(state, stream_mode="values"):
        if("messages" in step):
            print_messages(step["messages"])

    print("======= DRAFTER FINISHED =======")

if(__name__ == "__main__"):
    run_document_agent()