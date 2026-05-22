@echo off
title MikroKiller Test Lab
color 0A
echo.
echo  Starting MikroKiller Test Lab Server...
echo  Press Ctrl+C to stop.
echo.
python "%~dp0lab_server.py"
pause
