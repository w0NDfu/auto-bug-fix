import os
from backend.llm.mock import MockLLM
from backend.llm.openai_provider import OpenAIProvider

def get_llm():
    provider = os.getenv("LLM_PROVIDER", "mock").lower()
    if provider == "openai" or provider == "deepseek":
        return OpenAIProvider()
    return MockLLM()