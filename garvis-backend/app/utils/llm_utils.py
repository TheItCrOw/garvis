from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
import os


def instantiate_google_llm(model_name, temperature=0, max_retries=2, timeout=60):
    return ChatGoogleGenerativeAI(
                    model=model_name,
                    temperature=temperature,
                    max_retries=max_retries,
                    timeout = timeout,
                    )

def instantiate_ollama_llm(model_name, temperature=0, max_retries=2, timeout=60):
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    return ChatOllama(
                    model=model_name,
                    temperature=temperature,
                    max_retries=max_retries,
                    timeout = timeout,
                    base_url=base_url,
                    )

def instantiate_openai_llm(model_name, temperature=0, max_retries=2, timeout=60):
    return ChatOpenAI(
                    model=model_name,
                    temperature=temperature,
                    max_retries=max_retries,
                    timeout = timeout,
                    )