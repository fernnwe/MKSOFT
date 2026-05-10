#!/bin/bash
set -e

echo "========================================"
echo "  Despliegue - Sistema de Restaurante"
echo "========================================"

echo "[1/6] Construyendo imagenes..."
docker-compose build

echo "[2/6] Iniciando servicios..."
docker-compose up -d db redis

echo "[3/6] Esperando a que la base de datos este lista..."
sleep 10

echo "[4/6] Ejecutando migraciones..."
docker-compose run --rm web python manage.py migrate --no-input

echo "[5/6] Recopilando archivos estaticos..."
docker-compose run --rm web python manage.py collectstatic --no-input

echo "[6/6] Iniciando aplicacion..."
docker-compose up -d web daphne

echo "[7/7] Configurando backup automatico..."
docker-compose exec -d db sh -c "echo '0 3 * * * root /app/backup.sh' > /etc/cron.d/db_backup"

echo ""
echo "========================================"
echo "  Despliegue completado!"
echo "========================================"
echo ""
echo "Servicios disponibles:"
echo "  Web (Gunicorn): http://localhost:8000"
echo "  WebSockets (Daphne): http://localhost:8001"
echo "  Health Check: http://localhost:8000/health/"
echo ""
echo "Backups: /app/backups/ (diarios a las 3am, retencion 7 dias)"
echo ""
echo "Para crear un superusuario:"
echo "  docker-compose run --rm web python manage.py createsuperuser"
echo ""
echo "Para cargar datos de demo:"
echo "  docker-compose run --rm web python manage.py load_demo_data"
