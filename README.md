# Auto-Bug-Fix LLM (Multi-Agent with Reflection)

A runnable MVP that integrates LLMs into a multi-agent, closed-loop debugging system.

## Features
- Planner / Locator / Retriever / Coder / Tester / Reflector agents
- AST call graph (basic) + TF-IDF retriever (RAG-lite)
- Pluggable LLM providers: OpenAI-compatible, DeepSeek-compatible, or Mock
- Reflection loop: test -> error -> LLM-guided fix -> re-test
- FastAPI service

## Quick Start

```bash
pip install -r requirements.txt
export LLM_PROVIDER=mock   # or: openai / deepseek
export OPENAI_API_KEY=your_key   # if using openai-compatible
uvicorn backend.main:app --reload
```

Test:
```bash
curl -X POST http://127.0.0.1:8000/fix -H "Content-Type: application/json" -d '{"log":"ZeroDivisionError: division by zero"}'
```

## Switch Provider
- mock: no external calls, deterministic patch
- openai: set OPENAI_API_KEY and optionally OPENAI_BASE_URL
- deepseek: set OPENAI_API_KEY and OPENAI_BASE_URL to DeepSeek endpoint

## Project Structure
See folders under backend/ and repo/.