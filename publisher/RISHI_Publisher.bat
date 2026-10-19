@echo off
rem Double-click: opens the dashboard for batch.json in this folder's parent "batches" directory.
cd /d "%~dp0"
start "" http://127.0.0.1:8765
python rishi_publisher.py ui batches\batch.json --push --batch-size 10
