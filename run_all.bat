@echo off
rem SKYFORGE - launch everything: ground station server (4 detection maps) + the SKYFORGE dashboard.
cd /d "%~dp0"
set "PORT=8077"
set "SKYFORGE_PORT=%PORT%"
if not exist ".venv\Scripts\python.exe" (
  echo [!] Python environment .venv not found in %CD%
  echo     Create it first:  py -3.12 -m venv .venv  then install the requirements.
  pause
  exit /b 1
)

echo [1/2] Starting the ground station (mission replay + server on http://localhost:%PORT%) ...
start "SKYFORGE ground station - close this window to stop" cmd /k ".venv\Scripts\python.exe -m ground.demo"

echo [2/2] Opening the SKYFORGE dashboard ...
start "" "%~dp0UI UX\SKYFORGE Ground Station.html"

echo Waiting for the ground station to be ready (up to 90 s) ...
for /l %%i in (1,1,90) do (
  curl -s -o nul http://127.0.0.1:%PORT%/api/view && goto ready
  timeout /t 1 /nobreak >nul
)
echo [!] Ground station did not answer on port %PORT% - check its window for errors.
pause
exit /b 1

:ready
start "" http://localhost:%PORT%
echo Done. Dashboard and ground station are open.
timeout /t 3 /nobreak >nul
