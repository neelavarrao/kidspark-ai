#!/bin/bash

# Install dependencies
pip install -r requirements.txt

# Start the FastAPI application with the correct module path
uvicorn app.backend.main:app --host 0.0.0.0 --port $PORT