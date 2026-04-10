@echo off
REM Alice ADHD Companion - Backend API Server (Windows)

cd /d "%~dp0"

REM Activate virtual environment if exists
if exist "..\venv\Scripts\activate.bat" (
    call ..\venv\Scripts\activate.bat
)

REM Install dependencies
pip install -r requirements.txt -q

REM Start server
echo Starting Alice Backend API Server...
echo API URL: http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo.

uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload