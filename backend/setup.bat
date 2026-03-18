@echo off
echo ====================================================
echo  H&M Invoice Extractor - Setup
echo ====================================================
echo.

REM Check if .env exists
if not exist .env (
    echo Creating .env from template...
    copy .env.example .env
    echo.
    echo IMPORTANT: Open .env and add your GEMINI_API_KEY before running!
    echo.
)

REM Create virtual environment if not exists
if not exist venv (
    echo Creating Python virtual environment...
    python -m venv venv
)

REM Activate and install
echo Installing dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt

echo.
echo ====================================================
echo  Setup complete!
echo  1. Edit .env and add your GEMINI_API_KEY
echo  2. Run:  start.bat
echo ====================================================
pause
