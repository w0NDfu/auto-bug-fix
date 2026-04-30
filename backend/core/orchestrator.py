from backend.agents.locator import locate_bug
from backend.agents.coder import generate_patch
from backend.agents.validator import run_tests
from backend.agents.reflector import reflect_and_fix

MAX_RETRY = 3

def run_pipeline(log):
    context = locate_bug(log)

    for _ in range(MAX_RETRY):
        patch, test_code = generate_patch(context)
        success, error = run_tests(patch, test_code)

        if success:
            return {"status": "fixed", "patch": patch}

        context = reflect_and_fix(context, error)

    return {"status": "failed", "reason": error}
