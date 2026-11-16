@echo off
setlocal
cd /d "%~dp0"
echo Creating the Python environment in .venv (one time)...
python -m venv .venv
if errorlevel 1 goto :fail
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 goto :fail
python -m pip install -r requirements.txt
if errorlevel 1 goto :fail
echo.
echo Setup finished. Next: install VB-CABLE (see README), then double-click run_app.bat.
pause
exit /b 0

:fail
echo.
echo Setup failed. A very long folder path is the most common cause on Windows.
echo Move this folder to something short such as C:\deep-voice and run setup.bat again.
pause
exit /b 1
