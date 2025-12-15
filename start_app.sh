#!/bin/bash

echo "=== Installing dependencies for KidSpark AI ==="
uv pip install -r requirements.txt

echo "=== Starting KidSpark AI application ==="
uv run uvicorn app.backend.main:app --reload --host 0.0.0.0 --port 8000