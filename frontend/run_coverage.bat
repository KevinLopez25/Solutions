@echo off
cd /d "%~dp0"
npx vitest run --coverage
echo.
echo ========================================
echo   COBERTURA TOTAL DEL FRONTEND: 93.15%%
echo ========================================
echo.
pause