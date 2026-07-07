@echo off
echo Starting NutriChat...

echo.
echo [1/2] Starting FastAPI backend on port 8000...
start "NutriChat Backend" cmd /k "cd backend && venv\Scripts\activate && uvicorn main:app --reload --port 8000"

timeout /t 2 /nobreak >nul

echo [2/2] Starting Next.js frontend on port 3000...
start "NutriChat Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo Both servers are starting in separate windows.
echo  Backend:  http://localhost:8000
echo  Frontend: http://localhost:3000
echo.
pause
