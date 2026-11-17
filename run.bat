@echo off
setlocal

cd /d "%~dp0"

echo ===============================================
echo  AI Attendance System - Setup ^& Launch
echo ===============================================

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python was not found on PATH.
    echo Install Python 3.10 or 3.11 from https://www.python.org/downloads/
    echo and make sure to tick "Add Python to PATH" during install.
    pause
    exit /b 1
)

if exist "venv\Scripts\activate.bat" (
    echo [1/2] Virtual environment found, skipping setup.
    call venv\Scripts\activate.bat
) else (
    echo [1/2] No virtual environment found - creating one and installing dependencies...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    call venv\Scripts\activate.bat
    python -m pip install --upgrade pip >nul
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies.
        echo If this failed on dlib/face_recognition, see the
        echo "Installing dlib / face_recognition" section in README.md.
        pause
        exit /b 1
    )
)

echo [2/2] Starting the app...
streamlit run app.py

pause
endlocal
