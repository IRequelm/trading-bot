@echo off
echo Starting Trading Bot...
echo.

REM Check if virtual environment exists
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Install/update dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Start the web interface
echo Starting web interface...
echo Open your browser and go to: http://localhost:5000
echo Press Ctrl+C to stop the bot
echo.
python main.py web

pause
