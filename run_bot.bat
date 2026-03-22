@echo off
echo ====================================
echo Telegram YouTube Bot Launcher
echo ====================================
echo.

REM Check if virtual environment exists
if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo Virtual environment not found, using system Python
)

echo.
echo Starting bot...
echo Press Ctrl+C to stop the bot
echo.

python telegram_youtube_bot.py

pause
