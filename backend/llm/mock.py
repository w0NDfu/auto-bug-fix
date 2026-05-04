from backend.llm.base import LLMProvider

class MockLLM(LLMProvider):
    def chat(self, system: str, user: str) -> str:
        # Deterministic minimal patch for demo
        if "ZeroDivisionError" in user or "division by zero" in user:
            return (
                "PATCH:\n"
                "def divide(a, b):\n"
                "    if b == 0:\n"
                "        return 0\n"
                "    return a / b\n\n"
                "TESTS:\n"
                "from buggy_code import divide\n"
                "def test_divide():\n"
                "    assert divide(4,2) == 2\n"
                "    assert divide(4,0) == 0\n"
            )
        return "PATCH:\n# no-op\n\nTESTS:\n# no-op\n"