from backend.llm.factory import get_llm

SYSTEM_PROMPT = """You are a senior software engineer.
Given error logs and code context, produce:
1) A minimal PATCH (full file content) that fixes the bug
2) Pytest TESTS to validate the fix
Return in format:

PATCH:
<python code>

TESTS:
<python test code>
"""

def generate_patch(state, context):
    llm = get_llm()
    user = f"Log: {state.log}\nHints: {state.hints}\nContext:\n" + "\n\n".join(context.get("docs", []))
    out = llm.chat(SYSTEM_PROMPT, user)

    patch, tests = parse_sections(out)
    return patch, tests

def parse_sections(text: str):
    patch = ""
    tests = ""
    cur = None
    for line in text.splitlines():
        if line.strip().startswith("PATCH:"):
            cur = "patch"
            continue
        if line.strip().startswith("TESTS:"):
            cur = "tests"
            continue
        if cur == "patch":
            patch += line + "\n"
        elif cur == "tests":
            tests += line + "\n"
    return patch.strip() or "# no-op", tests.strip() or "# no-op"