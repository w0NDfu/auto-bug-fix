from backend.llm.factory import get_llm

SYSTEM = "You analyze test failures and propose concise hints to fix the code."

def reflect(state, error: str):
    llm = get_llm()
    user = f"Error:\n{error}\nHistory:\n{state.history}\nProvide a short hint."
    hint = llm.chat(SYSTEM, user)
    state.add_hint(hint.strip()[:200])
    return state