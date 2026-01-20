#!/usr/bin/env python3
"""
Task 9: Complete Research Assistant
Combines all LangGraph concepts: StateGraph, Nodes, Edges, Loops, Tools, and Memory
"""

import os
from typing import TypedDict, List, Literal
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from ddgs import DDGS
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

print("\n🤖 COMPLETE RESEARCH ASSISTANT")
print("=" * 50)
print("Combining all LangGraph concepts into a working assistant!")

# Initialize LLM
llm = ChatOpenAI(
    model=os.getenv("OPENAI_MODEL","gpt-4.1-nano"),
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_API_BASE")
)

# Complete state structure with memory
class ResearchState(TypedDict):
    topic: str
    research_questions: List[str]
    search_queries: List[str]
    search_results: List[str]
    key_findings: List[str]
    iteration: int
    max_iterations: int
    quality_score: float
    final_report: str
    status: str

def input_processor_node(state: ResearchState):
    """Process and validate input topic"""
    print(f"\n📥 Input Processor Node")
    print(f"   Topic: '{state['topic']}'")
    
    # Enhance topic for better research
    prompt = f"""Given this research topic: '{state['topic']}'
    Suggest a more specific research focus (one line):"""
    
    response = llm.invoke(prompt)
    enhanced_topic = response.content.strip()
    
    print(f"   Enhanced: '{enhanced_topic}'")
    
    return {
        "topic": enhanced_topic,
        "status": "topic_processed"
    }

def question_generator_node(state: ResearchState):
    """Generate research questions"""
    print(f"\n❓ Question Generator Node")
    
    prompt = f"""Generate 3 specific research questions about: {state['topic']}
    Questions should be searchable and factual.
    Return only the questions, one per line:"""
    
    response = llm.invoke(prompt)
    questions = response.content.strip().split('\n')
    questions = [q.strip() for q in questions if q.strip()][:3]
    
    print(f"   Generated {len(questions)} questions")
    
    # Accumulate questions
    all_questions = state.get("research_questions", []) + questions
    
    return {
        "research_questions": all_questions,
        "status": "questions_generated"
    }

def search_tool_node(state: ResearchState):
    """Search for information using DuckDuckGo"""
    print(f"\n🔍 Search Tool Node (Iteration {state['iteration'] + 1})")
    
    search_results = state.get("search_results", [])
    search_queries = state.get("search_queries", [])
    
    # Search for each question
    for question in state["research_questions"]:
        if question not in search_queries:  # Avoid duplicate searches
            print(f"   Searching: {question[:50]}...")
            
            try:
                ddgs = DDGS()
                results = ddgs.text(question, max_results=2)
                
                for result in results:
                    title = result.get('title', '')
                    body = result.get('body', '')
                    search_results.append(f"{title}: {body}")
                
                search_queries.append(question)
                
            except Exception as e:
                print(f"   ⚠️ Search error: {e}")
    
    print(f"   Total results: {len(search_results)}")
    
    return {
        "search_results": search_results,
        "search_queries": search_queries,
        "iteration": state["iteration"] + 1,
        "status": "search_completed"
    }

def analyzer_node(state: ResearchState):
    """Analyze search results and extract key findings"""
    print(f"\n🔬 Analyzer Node")
    
    if not state["search_results"]:
        return {"key_findings": ["No search results to analyze"], "quality_score": 0.0}
    
    # Use LLM to analyze results
    results_text = "\n".join(state["search_results"][:10])  # Limit to prevent token overflow
    
    prompt = f"""Analyze these search results about '{state['topic']}':

{results_text}

Extract 5 key findings. Return only the findings, one per line:"""
    
    response = llm.invoke(prompt)
    findings = response.content.strip().split('\n')
    findings = [f.strip() for f in findings if f.strip()][:5]
    
    # Accumulate findings
    all_findings = state.get("key_findings", []) + findings
    
    # Calculate quality score based on findings
    quality = min(len(all_findings) * 0.2, 1.0)
    
    print(f"   Extracted {len(findings)} new findings")
    print(f"   Quality score: {quality:.2f}")
    
    return {
        "key_findings": all_findings,
        "quality_score": quality,
        "status": "analysis_completed"
    }

def report_generator_node(state: ResearchState):
    """Generate final research report"""
    print(f"\n📝 Report Generator Node")
    
    # Compile all information
    prompt = f"""Create a comprehensive research report based on this information:

Topic: {state['topic']}

Research Questions:
{chr(10).join(state['research_questions'])}

Key Findings:
{chr(10).join(state['key_findings'])}

Number of sources consulted: {len(state['search_results'])}

Generate a well-structured report with:
1. Executive Summary
2. Key Findings
3. Conclusion

Keep it concise but informative:"""
    
    response = llm.invoke(prompt)
    report = response.content
    
    # Add metadata
    report += f"\n\n---\n📊 Research Metadata:\n"
    report += f"• Topic: {state['topic']}\n"
    report += f"• Questions Asked: {len(state['research_questions'])}\n"
    report += f"• Sources Consulted: {len(state['search_results'])}\n"
    report += f"• Key Findings: {len(state['key_findings'])}\n"
    report += f"• Research Iterations: {state['iteration']}\n"
    report += f"• Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    
    print(f"   Report generated ({len(report)} chars)")
    
    return {
        "final_report": report,
        "status": "report_completed"
    }

def should_continue_research(state: ResearchState) -> Literal["search", "report"]:
    """Router: Decide whether to continue searching or generate report"""
    print(f"\n🚦 Router Decision:")
    
    # Check iteration limit
    if state["iteration"] >= state["max_iterations"]:
        print(f"   → Max iterations reached ({state['max_iterations']})")
        return "report"
    
    # Check quality threshold
    if state["quality_score"] >= 0.8:
        print(f"   → Quality sufficient ({state['quality_score']:.2f})")
        return "report"
    
    # Check if we have enough findings
    if len(state.get("key_findings", [])) >= 10:
        print(f"   → Enough findings collected")
        return "report"
    
    print(f"   → Continue researching (iteration {state['iteration'] + 1})")
    return "search"

# Build the complete workflow
print("\n🏗️ Building Research Assistant workflow...")
workflow = StateGraph(ResearchState)

# Add all nodes
workflow.add_node("input", input_processor_node)
workflow.add_node("questions", question_generator_node)
workflow.add_node("search", search_tool_node)
workflow.add_node("analyze", analyzer_node)
workflow.add_node("report", report_generator_node)

# Define the flow with loop
workflow.add_edge(START, "input")
workflow.add_edge("input", "questions")
workflow.add_edge("questions", "search")
workflow.add_edge("search", "analyze")

# Conditional routing for loop
workflow.add_conditional_edges(
    "analyze",
    should_continue_research,
    {
        "search": "questions",  # Loop back to generate more questions
        "report": "report"      # Exit to report generation
    }
)

workflow.add_edge("report", END)

# Compile the assistant
assistant = workflow.compile()

print("✅ Research Assistant ready!")

# Test the complete assistant
print("\n" + "=" * 50)
print("🚀 TESTING RESEARCH ASSISTANT")
print("=" * 50)

test_topics = [
    "Benefits of LangGraph for AI agents",
    "State management in workflow systems"
]

for topic in test_topics:
    print(f"\n📚 Researching: '{topic}'")
    print("-" * 40)
    
    initial_state = {
        "topic": topic,
        "research_questions": [],
        "search_queries": [],
        "search_results": [],
        "key_findings": [],
        "iteration": 0,
        "max_iterations": 2,  # Limit iterations for demo
        "quality_score": 0.0,
        "final_report": "",
        "status": "initialized"
    }
    
    try:
        result = assistant.invoke(initial_state)
        
        print(f"\n" + "=" * 50)
        print("📊 RESEARCH COMPLETE!")
        print("=" * 50)
        print(f"\n{result['final_report']}")
        
    except Exception as e:
        print(f"❌ Error during research: {e}")

print("\n" + "=" * 50)
print("🎓 CONGRATULATIONS!")
print("=" * 50)
print("""
You've built a complete Research Assistant that combines:
✅ StateGraph for workflow management
✅ Nodes for processing steps
✅ Edges and routing for flow control
✅ Loops for iterative refinement
✅ Tools for external data (DuckDuckGo)
✅ State accumulation for memory

Your assistant can:
• Process research topics
• Generate questions dynamically
• Search for information
• Analyze and extract findings
• Loop to gather more data if needed
• Generate comprehensive reports

This is the power of LangGraph! 🚀
""")

# Save completion marker
try:
    with open('./root/research-complete.txt', 'w') as f:
        f.write('RESEARCH_COMPLETE\n')
        f.write('Task 9: Research assistant implementation completed successfully\n')
    print("\n✅ Completion marker saved to /root/research-complete.txt")
except:
    print("\n✅ Task 9: Research Assistant completed!")
