#!/bin/bash
set -e

REPO_URL="https://github.com/fernnwe/MKSOFT.git"
APP_DIR="/opt/mksoft"

echo "========================================"
echo "  Despliegue - Sistema de Restaurante"
echo "========================================"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: Ejecuta como root (sudo)."
    exit 1
fi

# Clone or pull repo
if [ -d "$APP_DIR" ]; then
    echo "[1/9] Actualizando repositorio..."
    cd "$APP_DIR"
    git pull
else
    echo "[1/9] Clonando repositorio..."
    git clone "$REPO_URL" "$APP_DIR"
    cd "$APP_DIR"
fi

# Copy .env.production as .env if not exists
if [ ! -f ".env" ]; then
    echo "[2/9] Creando .env desde .env.production..."
    cp .env.production .env
    echo "IMPORTANTE: Edita .env con tus credenciales reales antes de continuar."
    echo "  nano .env"
    exit 1
fi

# Export env vars for docker compose
set -a
source .env
set +a

echo "[3/9] Construyendo imagenes..."
docker compose build

echo "[4/9] Iniciando servicios (db, redis)..."
docker compose up -d db redis

echo "[5/9] Esperando base de datos..."
sleep 10

echo "[6/9] Ejecutando migraciones..."
docker compose run --rm web python manage.py migrate --no-input

echo "[7/9] Recopilando estaticos..."
docker compose run --rm web python manage.py collectstatic --no-input

echo "[8/9] Iniciando aplicacion..."
docker compose up -d web daphne

echo "[9/9] Configurando backup automatico (crontab)..."
(crontab -l 2>/dev/null || true; echo "0 3 * * * cd $APP_DIR && docker compose exec -T db pg_dump -U restaurante restaurante_db | gzip > $APP_DIR/backups/backup_\$(date +\"%Y%m%d_%H%M%S\").sql.gz && find $APP_DIR/backups -name 'backup_*.sql.gz' -mtime +7 -delete") | crontab -

echo ""
echo "========================================"
echo "  Despliegue completado!"
echo "========================================"
echo ""
echo "Servicios disponibles:"
echo "  Web: http://localhost:8000"
echo "  WebSockets (Daphne): http://localhost:8001"
echo "  Health Check: http://localhost:8000/health/"
echo ""
echo "Backups: $APP_DIR/backups/ (3am, retencion 7 dias)"
echo ""
echo "Para crear un superusuario:"
echo "  cd $APP_DIR && docker compose run --rm web python manage.py createsuperuser"
