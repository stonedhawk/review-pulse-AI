@echo off
REM Creates a virtual environment and installs dependencies.
cd /d "%~dp0"
python -m venv venv || exit /b 1
venv\Scripts\python -m pip install --upgrade pip || exit /b 1
venv\Scripts\pip install -r requirements.txt || exit /b 1
if not exist data mkdir data
echo.
echo Done. Next:
echo   venv\Scripts\activate
echo   python pulse.py demo
