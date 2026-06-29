@echo off
REM PocketAgent - Start both backend and frontend locally (Windows)
REM Usage: Double-click or run in Command Prompt

setlocal enabledelayedexpansion

set ROOT_DIR=%~dp0
set BACKEND_LOG=%ROOT_DIR%tmp\backend.log
set FRONTEND_LOG=%ROOT_DIR%tmp\frontend.log

if not exist "%ROOT_DIR%tmp\" mkdir "%ROOT_DIR%tmp\"

echo Starting backend (FastAPI)...
cd /d "%ROOT_DIR%backend"
start "PocketAgent-Backend" cmd /c "uvicorn main:app --reload --port 8000 --host 0.0.0.0 > "%BACKEND_LOG%" 2>&1"

echo Waiting for backend...
:wait_backend
timeout /t 2 /nobreak > nul
curl -s http://127.0.0.1:8000/health > nul 2>&1
if errorlevel 1 goto wait_backend
echo Backend ready at http://localhost:8000

echo.
echo Starting frontend (Next.js)...
cd /d "%ROOT_DIR%frontend"

REM Create frontend .env if missing
if not exist ".env" (
    echo Creating frontend/.env...
    set API_URL=http://127.0.0.1:8000
    set WC_ID=b986e72a6fa82c645da36c67550760ee
    (
        echo NEXT_PUBLIC_API_URL=!API_URL!
        echo NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=!WC_ID!
    ) > .env
)

start "PocketAgent-Frontend" cmd /c "npm run dev > "%FRONTEND_LOG%" 2>&1"

echo Waiting for frontend...
:wait_frontend
timeout /t 2 /nobreak > nul
curl -s -o nul -w "" http://127.0.0.1:3000 > nul 2>&1
if errorlevel 1 goto wait_frontend
echo Frontend ready at http://localhost:3000

echo.
echo ========================================
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:3000
echo   API Docs: http://localhost:8000/docs
echo ========================================
echo.
echo Both services are running in separate windows.
echo Close the windows or use Task Manager to stop them.
echo.

pause
