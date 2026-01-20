#!/usr/bin/env python3
"""
Task 3: StateGraph Demo - Shopping Cart
Shows how state persists and accumulates across nodes
"""

from typing import TypedDict, List
from langgraph.graph import StateGraph, START, END

print("\n🛒 STATEGRAPH DEMO - Shopping Cart")
print("=" * 40)

# Define state structure
class CartState(TypedDict):
    items: List[str]
    total: float
    status: str

def add_apple(state: CartState):
    """Add apple to cart - shows state accumulation"""
    print("\nStep 1: Adding apple ($5) to cart...")
    new_items = state["items"] + ["apple"]
    new_total = state["total"] + 5
    print(f"  → State: items={new_items}, total=${new_total}")
    return {
        "items": new_items,
        "total": new_total
    }

def add_banana(state: CartState):
    """Add banana to cart - shows accumulation continues"""
    print("\nStep 2: Adding banana ($3) to cart...")
    new_items = state["items"] + ["banana"]
    new_total = state["total"] + 3
    print(f"  → State: items={new_items}, total=${new_total}")
    return {
        "items": new_items,
        "total": new_total
    }

def checkout(state: CartState):
    """Complete purchase - shows state persistence"""
    print("\nStep 3: Processing checkout...")
    print(f"  → Final items: {state['items']}")
    print(f"  → Final total: ${state['total']}")
    return {
        "status": "paid"
    }

# Build the graph
print("\nBuilding StateGraph workflow...")
workflow = StateGraph(CartState)

# Add nodes
workflow.add_node("add_apple", add_apple)
workflow.add_node("add_banana", add_banana)
workflow.add_node("checkout", checkout)

# Define flow
workflow.set_entry_point("add_apple")
workflow.add_edge("add_apple", "add_banana")
workflow.add_edge("add_banana", "checkout")
workflow.add_edge("checkout", END)

# Compile and run
app = workflow.compile()

# Initial state
initial_state = {
    "items": [],
    "total": 0.0,
    "status": "pending"
}

print(f"\nInitial State: {initial_state}")
print("\nExecuting workflow...")

# Run the workflow
result = app.invoke(initial_state)

# Show final state
print("\n" + "=" * 40)
print("✅ FINAL STATE:")
print(f"  Items: {result['items']}")
print(f"  Total: ${result['total']}")
print(f"  Status: {result['status']}")

print("\n💡 Key Insights:")
print("  • State persisted across all nodes")
print("  • Each node added to the state")
print("  • Previous values were preserved")

# Save completion marker
try:
    with open('./root/stategraph_complete.txt', 'w') as f:
        f.write('StateGraph implementation complete\n')
        f.write(f'Final state: {result}\n')
except:
    pass  # Local testing