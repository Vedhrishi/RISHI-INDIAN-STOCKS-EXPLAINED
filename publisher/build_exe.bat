@echo off
rem Optional: builds RISHI_Publisher.exe (no Python needed to run it). Leave the exe inside this folder.
cd /d "%~dp0"
python -m pip install pyinstaller
python -m PyInstaller --onefile --windowed --name RISHI_Publisher rishi_app.py
copy /y dist\RISHI_Publisher.exe RISHI_Publisher.exe
echo Done: RISHI_Publisher.exe (ffmpeg and git must still be installed).
