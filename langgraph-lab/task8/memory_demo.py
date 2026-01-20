#!/usr/bin/env python3
"""
Task 8: Memory & State Accumulation Demo
Shows how state persists and accumulates across nodes
Building knowledge over multiple operations
"""

import os
from typing import TypedDict, List
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

print("\n💾 MEMORY & STATE ACCUMULATION DEMO")
print("=" * 40)

# Initialize LLM with environment variables
llm = ChatOpenAI(
    model=os.getenv("OPENAI_MODEL","openai/gpt-4.1-mini"),
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_API_BASE")
)

# Define state with accumulating fields
class MemoryState(TypedDict):
    topic: str
    questions: List[str]           # Accumulates questions
    search_results: List[str]      # Accumulates search results
    key_points: List[str]          # Accumulates key points
    knowledge_base: str            # Final accumulated knowledge
    operations_count: int          # Tracks operations

def generate_questions_node(state: MemoryState):
    """Generate research questions about the topic"""
    print(f"\n❓ Generate Questions Node")
    print(f"   Topic: {state['topic']}")
    
    prompt = f"""Generate 3 important research questions about: {state['topic']}
    Return only the questions, one per line:"""
    
    response = llm.invoke(prompt)
    questions = response.content.strip().split('\n')
    questions = [q.strip() for q in questions if q.strip()][:3]
    
    print(f"   → Generated {len(questions)} questions")
    for q in questions:
        print(f"      • {q[:50]}...")
    
    # ACCUMULATE: Add to existing questions
    all_questions = state.get("questions", []) + questions
    
    return {
        "questions": all_questions,
        "operations_count": state["operations_count"] + 1
    }

def search_node(state: MemoryState):
    """Simulate searching for each question"""
    print(f"\n🔍 Search Node")
    print(f"   Processing {len(state['questions'])} questions")
    
    search_results = state.get("search_results", [])
    
    # Simulate search for each question
    for question in state["questions"]:
        # Simulate search result
        result = f"Result for '{question[:30]}...': Found relevant information about {state['topic']}"
        search_results.append(result)
        print(f"   → Searched: {question[:40]}...")
    
    # ACCUMULATE: Add to existing search results
    return {
        "search_results": search_results,
        "operations_count": state["operations_count"] + 1
    }

def extract_key_points_node(state: MemoryState):
    """Extract key points from search results"""
    print(f"\n🎯 Extract Key Points Node")
    print(f"   Processing {len(state['search_results'])} search results")
    
    # Use LLM to extract key points
    results_text = "\n".join(state["search_results"])
    
    prompt = f"""Extract 5 key points from these search results about {state['topic']}:
    
{results_text}

Return only the key points, one per line:"""
    
    response = llm.invoke(prompt)
    new_points = response.content.strip().split('\n')
    new_points = [p.strip() for p in new_points if p.strip()][:5]
    
    print(f"   → Extracted {len(new_points)} key points")
    
    # ACCUMULATE: Add to existing key points
    all_points = state.get("key_points", []) + new_points
    
    return {
        "key_points": all_points,
        "operations_count": state["operations_count"] + 1
    }

def build_knowledge_base_node(state: MemoryState):
    """Build comprehensive knowledge base from accumulated state"""
    print(f"\n📚 Build Knowledge Base Node")
    print(f"   Synthesizing from:")
    print(f"      • {len(state['questions'])} questions")
    print(f"      • {len(state['search_results'])} search results")
    print(f"      • {len(state['key_points'])} key points")
    
    # Use LLM to synthesize everything
    prompt = f"""Create a comprehensive knowledge summary about {state['topic']}.

Questions explored:
{chr(10).join(state['questions'])}

Key points discovered:
{chr(10).join(state['key_points'])}

Provide a well-structured summary:"""
    
    response = llm.invoke(prompt)
    knowledge_base = response.content
    
    print(f"   → Built knowledge base ({len(knowledge_base)} chars)")
    
    return {
        "knowledge_base": knowledge_base,
        "operations_count": state["operations_count"] + 1
    }

def display_memory_state(state: MemoryState):
    """Display the accumulated state"""
    print(f"\n" + "=" * 50)
    print("📊 ACCUMULATED STATE SUMMARY")
    print("=" * 50)
    print(f"Topic: {state['topic']}")
    print(f"Total Operations: {state['operations_count']}")
    print(f"\n📝 Questions Generated: {len(state['questions'])}")
    for i, q in enumerate(state['questions'], 1):
        print(f"   {i}. {q[:60]}...")
    
    print(f"\n🔍 Search Results: {len(state['search_results'])}")
    
    print(f"\n🎯 Key Points: {len(state['key_points'])}")
    for i, p in enumerate(state['key_points'], 1):
        print(f"   {i}. {p[:60]}...")
    
    print(f"\n📚 Knowledge Base Preview:")
    print(state['knowledge_base'][:300] + "...")
    
    return state

# Build the workflow
print("\n🏗️ Building memory-enabled workflow...")
workflow = StateGraph(MemoryState)

# Add nodes
workflow.add_node("questions", generate_questions_node)
workflow.add_node("search", search_node)
workflow.add_node("extract", extract_key_points_node)
workflow.add_node("synthesize", build_knowledge_base_node)
workflow.add_node("display", display_memory_state)

# Define the flow
workflow.add_edge(START, "questions")
workflow.add_edge("questions", "search")
workflow.add_edge("search", "extract")
workflow.add_edge("extract", "synthesize")
workflow.add_edge("synthesize", "display")
workflow.add_edge("display", END)

# Compile the graph
app = workflow.compile()

# Test memory accumulation
print("\n" + "=" * 40)
print("🚀 RUNNING MEMORY ACCUMULATION TEST")
print("=" * 40)

# Test with different topics
test_topics = [
    "LangGraph memory management",
    "State accumulation patterns"
]

for topic in test_topics:
    print(f"\n🎯 Researching: '{topic}'")
    print("-" * 40)
    
    initial_state = {
        "topic": topic,
        "questions": [],
        "search_results": [],
        "key_points": [],
        "knowledge_base": "",
        "operations_count": 0
    }
    
    result = app.invoke(initial_state)
    
    print(f"\n✅ Research completed!")
    print(f"   Final state size:")
    print(f"   • Questions: {len(result['questions'])}")
    print(f"   • Results: {len(result['search_results'])}")
    print(f"   • Key Points: {len(result['key_points'])}")
    print(f"   • Knowledge Base: {len(result['knowledge_base'])} chars")

print("\n" + "=" * 40)
print("💡 KEY INSIGHTS ABOUT STATE ACCUMULATION")
print("=" * 40)
print("""
1. State persists across all nodes in the workflow
2. Lists and collections can accumulate data
3. Each node can read and add to existing state
4. State acts as the workflow's "memory"
5. Final nodes can synthesize accumulated knowledge

State Accumulation Pattern:
   • Read existing state: state.get("field", [])
   • Add new data: existing + new_data
   • Return updated state: {"field": accumulated_data}
""")

# Save completion marker
try:
    with open('./root/memory-complete.txt', 'w') as f:
        f.write('MEMORY_COMPLETE\n')
        f.write('Task 8: Memory and state accumulation completed successfully\n')
    print("\n✅ Completion marker saved to /root/memory-complete.txt")
except:
    # For local testing
    print("\n✅ Task 8: Memory demonstration completed!")