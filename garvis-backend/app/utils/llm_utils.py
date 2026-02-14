from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI


def instantiate_google_llm(model_name, temperature=0, max_retries=2, timeout=60):
    return ChatGoogleGenerativeAI(
                    model=model_name,
                    temperature=temperature,
                    max_retries=max_retries,
                    timeout = timeout)

def instantiate_ollama_llm(model_name, temperature=0, max_retries=2, timeout=60):
    return ChatOllama(
                    model=model_name,
                    temperature=temperature,
                    max_retries=max_retries,
                    timeout = timeout)

def instantiate_openai_llm(model_name, temperature=0, max_retries=2, timeout=60):
    return ChatOpenAI(
                    model=model_name,
                    temperature=temperature,
                    max_retries=max_retries,
                    timeout = timeout)