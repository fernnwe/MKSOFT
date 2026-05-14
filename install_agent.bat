@echo off
title MKSOFT Printer Agent - Instalador
echo ========================================
echo  MKSOFT Printer Agent - Instalacion
echo ========================================
echo.

set "APP_DIR=%LOCALAPPDATA%\MKSOFT\PrinterAgent"
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

echo Creando directorio: %APP_DIR%
if not exist "%APP_DIR%" mkdir "%APP_DIR%"

echo Instalando dependencias Python...
python -m pip install --quiet pywin32 requests 2>nul
if %errorlevel% neq 0 (
    echo ERROR: No se pudo instalar dependencias. Asegurate de tener Python instalado.
    pause
    exit /b 1
)

echo Copiando archivos...
copy /Y "printer_agent.py" "%APP_DIR%\printer_agent.py" >nul
copy /Y "printer_agent.vbs" "%APP_DIR%\printer_agent.vbs" >nul

echo Creando acceso directo en inicio de Windows...
copy /Y "%APP_DIR%\printer_agent.vbs" "%STARTUP_DIR%\MKSOFT Printer Agent.vbs" >nul

echo Iniciando agente...
wscript "%APP_DIR%\printer_agent.vbs"

echo.
echo ========================================
echo  Instalacion completada!
echo  El agente se iniciara automaticamente
echo  al iniciar sesion en Windows.
echo ========================================
echo.
echo  Ve a MKSOFT en el navegador, abre una factura
echo  y haz clic en "Agente Local" para imprimir.
echo.
pause
