#!/usr/bin/env python3
"""
Task 7: Tool Integration Demo
Shows how to integrate DuckDuckGo search tool with LangGraph nodes
"""

import os
from typing import TypedDict, List
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from ddgs import DDGS
from dotenv import load_dotenv

load_dotenv()
    
print("\n🔧 TOOL INTEGRATION DEMO - DuckDuckGo Search")
print("=" * 40)

# Initialize LLM with environment variables
llm = ChatOpenAI(
    model=os.getenv("OPENAI_MODEL", "openai/gpt-4.1-mini"),
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_API_BASE")
)

# Define state structure
class ToolState(TypedDict):
    query: str
    enhanced_query: str
    search_results: List[str]
    summary: str

def enhance_query_node(state: ToolState):
    """Use LLM to enhance the search query"""
    print(f"\n🎯 Enhance Query Node")
    print(f"   Original query: '{state['query']}'")
    
    # Use LLM to enhance the query
    prompt = f"""Enhance this search query to get better results. 
    Make it more specific and add relevant keywords.
    Original query: {state['query']}
    Enhanced query (return only the query, no explanation):"""
    
    response = llm.invoke(prompt)
    enhanced = response.content.strip()
    
    print(f"   Enhanced query: '{enhanced}'")
    
    return {"enhanced_query": enhanced}

def search_tool_node(state: ToolState):
    """Tool node: Uses DuckDuckGo to search the web"""
    print(f"\n🦆 Search Tool Node (DuckDuckGo)")
    
    query = state["enhanced_query"] or state["query"]
    print(f"   Searching for: '{query}'")
    
    # Use DuckDuckGo search tool
    try:
        ddgs = DDGS()
        results = ddgs.text(query, max_results=3)
        
        # Extract text from results
        search_results = []
        for i, result in enumerate(results, 1):
            title = result.get('title', 'No title')
            body = result.get('body', 'No description')
            search_results.append(f"{i}. {title}: {body}")
            print(f"   → Found result {i}: {title[:50]}...")
        
        if not search_results:
            search_results = ["No results found. Try a different query."]
            print("   → No results found")
            
    except Exception as e:
        print(f"   ⚠️ Search error: {e}")
        search_results = [f"Search error: {str(e)}. Using fallback data."]
    
    return {"search_results": search_results}

def summarize_node(state: ToolState):
    """Use LLM to summarize the search results"""
    print(f"\n📝 Summarize Node")
    
    results_text = "\n".join(state["search_results"])
    
    prompt = f"""Summarize these search results for the query '{state['query']}':

{results_text}

Provide a concise, helpful summary:"""
    
    response = llm.invoke(prompt)
    summary = response.content
    
    print(f"   → Generated summary ({len(summary)} chars)")
    
    return {"summary": summary}

def format_output_node(state: ToolState):
    """Format the final output"""
    print(f"\n📤 Format Output Node")
    
    output = f"""
{'='*50}
🔍 SEARCH RESULTS
{'='*50}
Query: {state['query']}
Enhanced: {state['enhanced_query']}

Results Found: {len(state['search_results'])}

Summary:
{state['summary']}
{'='*50}
"""
    print(output)
    return state

# Build the workflow
print("\n🏗️ Building tool-integrated workflow...")
workflow = StateGraph(ToolState)

# Add nodes (including tool node)
workflow.add_node("enhance_query", enhance_query_node)
workflow.add_node("search_tool", search_tool_node)  # This is our TOOL NODE
workflow.add_node("summarize", summarize_node)
workflow.add_node("format", format_output_node)

# Define the flow
workflow.add_edge(START, "enhance_query")
workflow.add_edge("enhance_query", "search_tool")
workflow.add_edge("search_tool", "summarize")
workflow.add_edge("summarize", "format")
workflow.add_edge("format", END)

# Compile the graph
app = workflow.compile()

# Test the tool integration
print("\n" + "=" * 40)
print("🚀 RUNNING TOOL INTEGRATION TESTS")
print("=" * 40)

test_queries = [
    "What is LangGraph used for?",
    "How to build AI agents?",
    "DuckDuckGo search API"
]

for query in test_queries:
    print(f"\n🔎 Testing: '{query}'")
    print("-" * 40)
    
    initial_state = {
        "query": query,
        "enhanced_query": "",
        "search_results": [],
        "summary": ""
    }
    
    try:
        result = app.invoke(initial_state)
        print(f"✅ Search completed successfully")
    except Exception as e:
        print(f"❌ Error during search: {e}")

print("\n" + "=" * 40)
print("💡 KEY INSIGHTS ABOUT TOOLS")
print("=" * 40)
print("""
1. Tools are just special nodes that interact with external services
2. DuckDuckGo is free and requires no API key
3. Tool nodes can fail - always handle errors gracefully
4. Combine tools with LLM nodes for enhanced functionality
5. Tools extend LangGraph's capabilities beyond just LLM calls
""")

print("\n🎨 Tool Node Pattern:")
print("""
def tool_node(state):
    # 1. Extract parameters from state
    # 2. Call external tool/API
    # 3. Process results
    # 4. Return state updates
    return {"tool_results": results}
""")

# Save completion marker
try:
    with open('./root/tools-complete.txt', 'w') as f:
        f.write('TOOLS_COMPLETE\n')
        f.write('Task 7: Tool integration completed successfully\n')
    print("\n✅ Completion marker saved to /root/tools-complete.txt")
except:
    # For local testing
    print("\n✅ Task 7: Tool integration demonstration completed!")