# Sistema de Gestion de Restaurante

Sistema web completo para la gestion de restaurantes con control de comandas, facturacion, mesas, inventario y stock. Desarrollado con Python y Django, con interfaz responsive para uso en celulares y tablets por los meseros.

## Caracteristicas

- **Gestion de Mesas**: Plano visual de mesas con estados en tiempo real (Libre, Ocupada, Reservada, Mantenimiento)
- **Comandas**: Creacion y seguimiento de comandas con envio a cocina
- **Vista Cocina**: Pantalla de cocina con actualizacion en tiempo real via WebSockets
- **Facturacion**: Generacion de facturas con soporte para multiples metodos de pago
- **Inventario**: Control de stock con alertas de stock bajo y registro de movimientos
- **Productos**: Catalogo de productos con categorias, precios y costos
- **Meseros**: Gestion de meseros con PIN y seguimiento de comandas
- **API REST**: API completa para integracion con aplicaciones moviles
- **Multiplataforma**: Diseño responsive optimizado para celulares y tablets
- **Sincronizacion en Tiempo Real**: WebSockets para actualizacion instantanea

## Tecnologias

- **Backend**: Python 3.10+, Django 4.2
- **API**: Django REST Framework
- **Tiempo Real**: Django Channels (WebSockets)
- **Frontend**: Bootstrap 5, Bootstrap Icons
- **Base de Datos**: SQLite (desarrollo), PostgreSQL (produccion)
- **Formularios**: Crispy Forms con Bootstrap 5

## Instalacion

### 1. Crear entorno virtual

```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar variables de entorno

```bash
cp .env.example .env
```

Edita `.env` con la configuracion de tu restaurante.

### 4. Migraciones

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Cargar datos de demostracion

```bash
python manage.py load_demo_data
python manage.py createsuperuser
```

### 6. Ejecutar servidor

```bash
python manage.py runserver
```

Accede a `http://localhost:8000`

## Credenciales de Prueba

| Usuario | Contraseña | Rol |
|---------|------------|-----|
| admin | admin123 | Administrador |
| mesero1 | mesero123 | Mesero |
| mesero2 | mesero123 | Mesero |
| cocina | cocina123 | Cocina |

## Estructura del Proyecto

```
openCode/
├── config/              # Configuracion principal de Django
│   ├── settings.py      # Configuracion general
│   ├── urls.py          # URLs principales
│   ├── asgi.py          # Configuracion ASGI (WebSockets)
│   └── wsgi.py          # Configuracion WSGI
├── core/                # App base (usuarios, dashboard)
├── mesas/               # Gestion de mesas
├── meseros/             # Gestion de meseros
├── productos/           # Catalogo de productos y categorias
├── comandas/            # Comandas y vista de cocina
├── inventario/          # Control de inventario y stock
├── facturacion/         # Facturacion y pagos
├── templates/           # Templates HTML
│   ├── base.html
│   ├── core/
│   ├── mesas/
│   ├── comandas/
│   ├── inventario/
│   ├── facturacion/
│   ├── productos/
│   └── meseros/
├── static/              # Archivos estaticos (CSS, JS)
└── manage.py
```

## API REST

La API esta disponible en `/api/` con los siguientes endpoints:

- `GET /api/mesas/` - Listar mesas
- `POST /api/mesas/{id}/cambiar_estado/` - Cambiar estado de mesa
- `GET /api/productos/` - Listar productos
- `GET /api/categorias/` - Listar categorias
- `GET /api/comandas/` - Listar comandas
- `POST /api/comandas/{id}/agregar_item/` - Agregar item a comanda
- `POST /api/comandas/{id}/enviar_cocina/` - Enviar comanda a cocina
- `POST /api/comandas/{id}/cerrar/` - Cerrar comanda
- `GET /api/facturas/` - Listar facturas

## Uso en Moviles

El sistema esta optimizado para uso en celulares y tablets:

1. Los meseros pueden acceder desde cualquier dispositivo
2. La navegacion es responsive con menu colapsable
3. Las comandas se actualizan en tiempo real
4. La vista de cocina muestra las comandas pendientes
5. Todo sincronizado automaticamente via WebSockets

## Configuracion para Produccion

### Opcion 1: Docker (Recomendada)

```bash
cp .env.production .env
# Editar .env con tus credenciales de produccion

chmod +x deploy.sh
./deploy.sh
```

### Opcion 2: Manual

```bash
# 1. Instalar dependencias de produccion
pip install -r requirements.txt
pip install gunicorn psycopg2-binary channels-redis daphne

# 2. Configurar entorno
cp .env.production .env
# Editar .env con SECRET_KEY, ALLOWED_HOSTS, DB_PASSWORD, etc.

# 3. Configurar base de datos PostgreSQL
# Crear la base de datos y usuario en PostgreSQL

# 4. Migrar y recopilar estaticos
python manage.py migrate --no-input
python manage.py collectstatic --no-input

# 5. Ejecutar con Gunicorn + Daphne
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4 &
daphne config.asgi:application --bind 0.0.0.0 --port 8001 &
```

### Checklist de Produccion

- [ ] Cambiar `SECRET_KEY` a un valor seguro y unico
- [ ] Configurar `ALLOWED_HOSTS` con tu dominio
- [ ] Usar PostgreSQL en lugar de SQLite
- [ ] Configurar Redis para WebSockets
- [ ] Habilitar HTTPS con certificado SSL
- [ ] Configurar Nginx como reverse proxy
- [ ] Crear superusuario con `createsuperuser`
- [ ] Configurar backups de base de datos
- [ ] Monitorear logs de errores

## Licencia

MIT
