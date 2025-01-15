@echo off
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    pip install pyinstaller
)

pyinstaller --onefile --noconsole --strip "BSM.py"

if exist "BSM.exe" del "BSM.exe"
move "dist\BSM.exe" .\