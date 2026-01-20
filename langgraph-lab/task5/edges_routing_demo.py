#!/usr/bin/env python3
"""
Task 5: Edges & Routing Demo - Email Processing System
Shows normal edges, conditional routing, and workflow control
"""

from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END

class EmailState(TypedDict):
    email_text: str
    spam_score: float
    category: str
    priority: str

# Simple nodes for processing
def analyze_email(state: EmailState):
    """Analyze email content"""
    text = state["email_text"].lower()
    
    # Simple spam scoring
    spam_words = ["free", "winner", "click here"]
    score = sum(1 for word in spam_words if word in text) / 3
    
    print(f"📧 Analyzing: '{state['email_text'][:50]}...'")
    print(f"   Spam score: {score:.2f}")
    
    return {"spam_score": score}

def process_normal(state: EmailState):
    """Process normal emails"""
    print("✅ Processing as normal email")
    return {"category": "inbox", "priority": "normal"}

def process_spam(state: EmailState):
    """Handle spam emails"""
    print("🚫 Moving to spam folder")
    return {"category": "spam", "priority": "blocked"}

def process_important(state: EmailState):
    """Handle important emails"""
    print("⭐ Marking as important")
    return {"category": "inbox", "priority": "high"}

# Router function for conditional edges
def email_router(state: EmailState) -> Literal["spam", "important", "normal"]:
    """Route based on email characteristics"""
    
    if state["spam_score"] > 0.6:
        return "spam"
    elif "urgent" in state["email_text"].lower() or "important" in state["email_text"].lower():
        return "important"
    else:
        return "normal"

# Build the workflow
print("Building email processing workflow...")
workflow = StateGraph(EmailState)

# Add nodes
workflow.add_node("analyze", analyze_email)
workflow.add_node("normal", process_normal)
workflow.add_node("spam", process_spam)
workflow.add_node("important", process_important)

# Add edges - the control flow!

# 1. Normal edge: Start -> analyze
workflow.add_edge(START, "analyze")

# 2. Conditional edges: analyze -> (spam/important/normal)
workflow.add_conditional_edges(
    "analyze",
    email_router,
    {
        "spam": "spam",
        "important": "important",
        "normal": "normal"
    }
)

# 3. Normal edges: all paths -> END
workflow.add_edge("spam", END)
workflow.add_edge("important", END)
workflow.add_edge("normal", END)

# Compile and test
app = workflow.compile()

# Test emails
test_emails = [
    "Meeting tomorrow at 3pm",
    "You are a WINNER! Click here for FREE prize!",
    "URGENT: Server down, need immediate help",
    "Check out these cat photos"
]

print("\n" + "="*50)
print("🚀 Testing Email Routing System")
print("="*50)

for email in test_emails:
    print(f"\n{'='*50}")
    result = app.invoke({
        "email_text": email,
        "spam_score": 0.0,
        "category": "",
        "priority": ""
    })
    print(f"Result: {result['category']} (priority: {result['priority']})")

print("\n✨ Edge & Routing Concepts Demonstrated:")
print("  • Normal edges for fixed flow (START->analyze, nodes->END)")
print("  • Conditional routing based on state (spam score, keywords)")
print("  • Router function returns path decision")
print("  • Multiple paths converge at END")

# Save completion marker
with open('./root/edges_routing_complete.txt', 'w') as f:
    f.write('EDGES_ROUTING_COMPLETE')