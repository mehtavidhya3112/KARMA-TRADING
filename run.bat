@echo off
title KARMA PA Scanner
color 0B

echo.
echo  ============================================================
echo   KARMA PRICE ACTION - PDH/PDL BREAKOUT SCANNER
echo   NSE Multi-Stock Scanner
echo  ============================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python not found. Please install Python 3.10-3.13
    echo  Download from: https://www.python.org/downloads/
    pause
    exit /b
)

echo  [1/2] Installing dependencies...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo  ERROR: Failed to install dependencies.
    echo  Try manually: pip install -r requirements.txt
    pause
    exit /b
)

echo  [2/2] Starting KARMA Scanner...
echo.
echo  App will open at: http://localhost:8501
echo  Press Ctrl+C to stop the app.
echo.

python -m streamlit run app.py --server.port 8501 --server.headless false

pause
