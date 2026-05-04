import os
from backend.agents.planner import plan_task
from backend.agents.locator import locate_bug
from backend.agents.retriever import retrieve
from backend.agents.coder import generate_patch
from backend.agents.tester import run_tests
from backend.agents.reflector import reflect
from backend.memory.state import State

MAX_ITER = int(os.getenv("MAX_ITER", "5"))

def run_pipeline(log: str):
    state = State(log)
    plan = plan_task(log)

    for i in range(MAX_ITER):
        loc_ctx = locate_bug(state, plan)
        ret_ctx = retrieve(state, loc_ctx)
        patch, tests = generate_patch(state, ret_ctx)

        ok, out = run_tests(patch, tests)
        state.add_history({"iter": i, "ok": ok, "out": out[:500]})

        if ok:
            return {
                "status": "fixed",
                "iterations": i + 1,
                "patch": patch,
                "tests": tests
            }

        state = reflect(state, out)

    return {
        "status": "failed",
        "history": state.history,
        "hints": state.hints
    }