@echo off
echo Starting NutriChat...
echo.
echo [1/2] Starting FastAPI backend (port 8000)...
start "NutriChat Backend" cmd /k "cd /d %~dp0backend && venv\Scripts\activate && uvicorn main:app --reload --port 8000"
timeout /t 2 /nobreak >nul
echo [2/2] Starting Vite frontend (port 5173)...
start "NutriChat Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"
echo.
echo  Backend:   http://localhost:8000
echo  Frontend:  http://localhost:5173
echo.
pause
