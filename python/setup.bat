@echo off
REM Initial setup for Windows
REM Creates a virtual environment in .venv and installs the required packages.
cd /d "%~dp0"

python --version || (echo Python not found. Install Python 3.9+ from python.org and tick "Add to PATH". & pause & exit /b 1)

python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo.
echo Setup complete. Checking the installation...
python check_setup.py
echo.
echo Next time, activate the environment first:  .venv\Scripts\activate
echo Then run, for example:                      python "TOPSIS-AHP method.py"
echo Web frontend:                               python run_frontend.py
pause
