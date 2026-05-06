@echo off
echo ========================================
echo   Sistema de Gestion de Restaurante
echo ========================================
echo.

if not exist "venv\" (
    echo Creando entorno virtual...
    python -m venv venv
    call venv\Scripts\activate
    echo Instalando dependencias...
    pip install django djangorestframework django-crispy-forms crispy-bootstrap5 channels Pillow python-dotenv whitenoise
) else (
    call venv\Scripts\activate
)

echo.
echo Ejecutando migraciones...
py manage.py migrate --no-input

echo.
echo Cargando datos de demostracion (si no existen)...
py manage.py load_demo_data

echo.
echo ========================================
echo   Servidor iniciado en:
echo   http://localhost:8000
echo ========================================
echo.
echo Credenciales de prueba:
echo   Admin: admin / admin123
echo   Mesero: mesero1 / mesero123
echo   Cocina: cocina / cocina123
echo.

py manage.py runserver
