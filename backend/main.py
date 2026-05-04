from fastapi import FastAPI
from pydantic import BaseModel
from backend.core.orchestrator import run_pipeline

app = FastAPI()

class FixRequest(BaseModel):
    log: str

@app.post("/fix")
def fix(req: FixRequest):
    return run_pipeline(req.log)