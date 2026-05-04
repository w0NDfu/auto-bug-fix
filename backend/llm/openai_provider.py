import os
from backend.llm.base import LLMProvider

class OpenAIProvider(LLMProvider):
    def __init__(self):
        from openai import OpenAI
        base_url = os.getenv("OPENAI_BASE_URL") or None
        self.client = OpenAI(base_url=base_url)
        self.model = os.getenv("MODEL_NAME", "gpt-4o-mini")

    def chat(self, system: str, user: str) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
        )
        return resp.choices[0].message.content