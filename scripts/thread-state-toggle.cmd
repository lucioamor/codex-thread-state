@echo off
setlocal
python "%~dp0..\thread_state.py" toggle
if errorlevel 1 pause
