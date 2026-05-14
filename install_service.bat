@echo off
title MKSOFT Printer Agent - Instalacion como Servicio Windows
echo ========================================
echo  Instalacion como Servicio de Windows
echo ========================================
echo  Esto hara que el agente funcione SIEMPRE,
echo  incluso sin que nadie inicie sesion.
echo ========================================
echo.

:: Requiere privilegios de administrador
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Ejecuta como Administrador
    echo (clic derecho ^> "Ejecutar como administrador")
    pause
    exit /b 1
)

set "APP_DIR=%LOCALAPPDATA%\MKSOFT\PrinterAgent"
set "SERVICE_NAME=MKSOFTPrinterAgent"

echo Instalando Python y dependencias...
python -m pip install --quiet pywin32 requests 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Python no instalado o pip fallo
    pause
    exit /b 1
)

echo Creando directorio: %APP_DIR%
if not exist "%APP_DIR%" mkdir "%APP_DIR%"

copy /Y "printer_agent.py" "%APP_DIR%\printer_agent.py" >nul

echo Creando servicio "%SERVICE_NAME%"...
sc create "%SERVICE_NAME%" binPath="cmd /c python %APP_DIR%\printer_agent.py --service" start=auto DisplayName="MKSOFT Printer Agent"
sc description "%SERVICE_NAME%" "Agente de impresion termica para MKSOFT. Envia tickets ESC/POS a la impresora."

echo Iniciando servicio...
net start "%SERVICE_NAME%"

echo.
echo ========================================
echo  Instalacion completada!
echo  El servicio se inicio correctamente.
echo  Funcionara incluso sin sesion de usuario.
echo ========================================
echo.
echo  Para desinstalar:  sc delete "%SERVICE_NAME%"
echo  Para reiniciar:    net stop "%SERVICE_NAME%" ^&^& net start "%SERVICE_NAME%"
echo.
pause
