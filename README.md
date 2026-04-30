# Auto Bug Fix MVP

## Run
pip install -r requirements.txt
uvicorn backend.main:app --reload

## Test
curl -X POST http://127.0.0.1:8000/fix -H "Content-Type: application/json" -d '{"log":"ZeroDivisionError"}'
