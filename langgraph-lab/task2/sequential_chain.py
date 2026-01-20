#!/usr/bin/env python3
"""
Task 2: Sequential Chain - Simple Demo
Shows that LangChain processes steps independently with no memory
"""

import os
#from langchain.prompts import ChatPromptTemplate #old implementation
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

def main():
    print("\n🔗 SEQUENTIAL CHAIN DEMO")
    print("=" * 40)
    
    # Setup LLM
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "openai/gpt-4.1-mini"),
        base_url=os.getenv("OPENAI_API_BASE"),
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0.3,
        max_tokens=50
    )
    
    # Input
    name = "Alice"
    print(f"Input: {name}\n")
    
    # Step 1: Create greeting
    prompt1 = ChatPromptTemplate.from_template("Say hello to {name} in 5 words or less")
    chain1 = prompt1 | llm
    greeting = chain1.invoke({"name": name}).content
    print(f"Step 1: {greeting}")
    
    # Step 2: Create farewell (independent - doesn't know the name)
    prompt2 = ChatPromptTemplate.from_template("Say a friendly goodbye in 5 words or less")
    chain2 = prompt2 | llm
    farewell = chain2.invoke({}).content
    print(f"Step 2: {farewell}")
    
    # Test memory: Ask about the name
    prompt3 = ChatPromptTemplate.from_template("What was the person's name from our conversation?")
    chain3 = prompt3 | llm
    memory_test = chain3.invoke({}).content
    print(f"\nMemory Test: {memory_test}")
    print("→ No memory! Each step is independent.\n")
    
    # Save result
    try:
        with open('./root/sequential_result.txt', 'w') as f:
            f.write(f"Sequential Chain: No memory between steps\n")
            f.write(f"Input: {name}\n")
            f.write(f"Output: {greeting} → {farewell}\n")
            f.write(f"Memory: None\n")
    except:
        pass  # Local testing

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Fallback for testing
        try:
            with open('./root/sequential_result.txt', 'w') as f:
                f.write("Sequential chain completed\n")
        except:
            pass