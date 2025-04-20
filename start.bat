@echo off
echo Loading. Please wait...
Python\Scripts\playwright.exe install chromium --only-shell
Python\python.exe script.py
pause