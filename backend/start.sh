#!/bin/bash
# Alice ADHD Companion - Backend API Server

cd "$(dirname "$0")"

# Activate virtual environment if exists
if [ -d "../venv" ]; then
    source ../venv/bin/activate
fi

# Install dependencies
pip install -r requirements.txt -q

# Start server
echo "Starting Alice Backend API Server..."
echo "API URL: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo ""

uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload