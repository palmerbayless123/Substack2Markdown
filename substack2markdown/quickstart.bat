@echo off
REM Quick Start Script for Substack2Markdown (Windows)
REM Run this script to set up the project quickly

echo ==========================================
echo    Substack2Markdown Quick Setup
echo ==========================================

REM Check Python version
echo.
echo Checking Python version...
python --version >nul 2>&1
if errorlevel 1 (
    echo X Python is not installed. Please install Python 3.8+ first.
    echo    Download from: https://python.org/downloads/
    pause
    exit /b 1
)
python --version
echo + Python found

REM Create virtual environment
echo.
echo Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo X Failed to create virtual environment
    pause
    exit /b 1
)
echo + Virtual environment created

REM Activate virtual environment
echo.
echo Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo X Failed to activate virtual environment
    pause
    exit /b 1
)
echo + Virtual environment activated

REM Install dependencies
echo.
echo Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo X Failed to install dependencies
    pause
    exit /b 1
)
echo + Dependencies installed

REM Create .env file from example
if not exist .env (
    echo.
    echo Creating .env configuration file...
    copy .env.example .env
    echo + Created .env file
    echo.
    echo ==========================================
    echo    IMPORTANT: Configure your .env file
    echo ==========================================
    echo.
    echo Edit the .env file with your Substack URL:
    echo.
    echo   notepad .env
    echo.
    echo Set at minimum:
    echo   SUBSTACK_URL=https://your-publication.substack.com
    echo.
)

REM Display usage instructions
echo.
echo ==========================================
echo    Setup Complete!
echo ==========================================
echo.
echo Usage:
echo.
echo   1. Edit .env with your Substack URL:
echo      notepad .env
echo.
echo   2. Activate the virtual environment:
echo      venv\Scripts\activate
echo.
echo   3. Run the scraper:
echo      python main.py              # Download all posts
echo      python main.py --list-only  # List available posts
echo      python main.py --help       # Show all options
echo.
echo For more details, see README.md
echo.
pause
