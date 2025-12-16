#!/bin/bash

# Set PORT environment variable to mimic Render
export PORT=8000

# Test the same command that Render will use
echo "Testing Render startup command..."
uvicorn app.backend.main:app --host 0.0.0.0 --port $PORT