from fastapi import FastAPI
from backend.core.orchestrator import run_pipeline

app = FastAPI()

@app.post("/fix")
def auto_fix(payload: dict):
    log = payload.get("log", "")
    result = run_pipeline(log)
    return {"result": result}
