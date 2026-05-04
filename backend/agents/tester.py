from backend.core.sandbox import run_pytest

def run_tests(patch, tests):
    return run_pytest(patch, tests)