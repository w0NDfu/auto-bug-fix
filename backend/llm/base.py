from abc import ABC, abstractmethod

class LLMProvider(ABC):
    @abstractmethod
    def chat(self, system: str, user: str) -> str:
        ...