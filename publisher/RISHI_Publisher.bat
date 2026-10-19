@echo off
rem Double-click to open the RISHI Publisher app (needs Python 3.9+ from python.org, "tcl/tk" option ticked, and ffmpeg + git on PATH).
cd /d "%~dp0"
start "" pythonw rishi_app.py
