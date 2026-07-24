@echo off
echo Starting Complain 24 Backend Server...

:: Start the python Flask server in a new command window
start "Complain 24 Server" cmd /k "python app.py"

echo Waiting for server to start...
:: Wait 2 seconds
timeout /t 2 /nobreak > NUL

:: Open the default web browser to the app
echo Opening in browser...
start http://localhost:5000/

echo Done! You can close this window now. (Leave the server window running)
pause
