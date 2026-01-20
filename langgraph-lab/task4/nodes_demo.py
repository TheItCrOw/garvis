#!/usr/bin/env python3
"""
Task 4: Nodes Demo - Different Types of Nodes
Shows how nodes process state and work together
"""

from typing import TypedDict
from langgraph.graph import StateGraph, START, END

print("\n🔨 NODES DEMO - Your Workflow Workers")
print("=" * 40)

# Define state structure
class WorkflowState(TypedDict):
    text: str
    word_count: int
    sentiment: str
    output: str

def input_node(state: WorkflowState):
    """Node 1: Validates and prepares input"""
    print("\n📥 Input Node: Receiving text...")
    text = state.get("text", "").strip()
    print(f"   → Received: '{text}'")
    return {"text": text}

def analyze_node(state: WorkflowState):
    """Node 2: Analyzes text properties"""
    print("\n🔍 Analyze Node: Processing text...")
    words = len(state["text"].split())
    print(f"   → Word count: {words}")
    return {"word_count": words}

def sentiment_node(state: WorkflowState):
    """Node 3: Determines sentiment"""
    print("\n😊 Sentiment Node: Checking mood...")
    
    positive_words = ["good", "great", "excellent", "happy", "amazing"]
    negative_words = ["bad", "terrible", "awful", "horrible", "sad"]
    
    text_lower = state["text"].lower()
    
    # Count positive and negative words
    pos_count = sum(1 for word in positive_words if word in text_lower)
    neg_count = sum(1 for word in negative_words if word in text_lower)
    
    if pos_count > neg_count:
        sentiment = "positive 😊"
    elif neg_count > pos_count:
        sentiment = "negative 😔"
    elif state["word_count"] < 5:
        sentiment = "neutral 😐"
    else:
        sentiment = "mixed 🤔"
    
    print(f"   → Sentiment: {sentiment}")
    return {"sentiment": sentiment}

def output_node(state: WorkflowState):
    """Node 4: Formats final output"""
    print("\n📤 Output Node: Generating result...")
    
    # Create formatted output
    output = f"\n{'='*40}\n"
    output += f"📊 ANALYSIS COMPLETE\n"
    output += f"{'='*40}\n"
    output += f"📝 Text: '{state['text'][:50]}{'...' if len(state['text']) > 50 else ''}'\n"
    output += f"📏 Word Count: {state['word_count']} words\n"
    output += f"💭 Sentiment: {state['sentiment']}\n"
    output += f"{'='*40}"
    
    return {"output": output}

# Build the workflow
print("\nBuilding workflow with 4 nodes...")
workflow = StateGraph(WorkflowState)

# Add all nodes
workflow.add_node("input", input_node)
workflow.add_node("analyze", analyze_node)
workflow.add_node("sentiment", sentiment_node)
workflow.add_node("output", output_node)

# Connect nodes in sequence
print("Connecting nodes: input → analyze → sentiment → output")
workflow.add_edge(START, "input")
workflow.add_edge("input", "analyze")
workflow.add_edge("analyze", "sentiment")
workflow.add_edge("sentiment", "output")
workflow.add_edge("output", END)

# Compile the graph
app = workflow.compile()

# Test with different examples
test_texts = [
    "This is a great example of how nodes work together!",
    "I feel bad about this terrible situation.",
    "Just a normal text.",
]

print("\n" + "="*40)
print("🚀 RUNNING WORKFLOW TESTS")
print("="*40)

for i, text in enumerate(test_texts, 1):
    print(f"\n--- Test {i} ---")
    result = app.invoke({"text": text})
    print(result["output"])

# Additional demonstration of node types
print("\n" + "="*40)
print("💡 KEY INSIGHTS ABOUT NODES")
print("="*40)
print("""
1. **Input Node**: Validates and prepares data
2. **Analyze Node**: Processes and transforms data
3. **Sentiment Node**: Makes decisions based on state
4. **Output Node**: Formats and presents results

Each node:
- Receives the current state
- Performs its specific task
- Returns updates to the state
- Passes control to the next node

Nodes are the building blocks of your workflow!
""")

# Save completion marker
try:
    with open('./root/nodes-complete.txt', 'w') as f:
        f.write('NODES_COMPLETE\n')
        f.write('Task 4: Nodes demonstration completed successfully\n')
    print("\n✅ Completion marker saved to /root/nodes-complete.txt")
except:
    # For local testing
    print("\n✅ Task 4: Nodes demonstration completed!")