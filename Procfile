web: gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --timeout 120 --workers 2
daphne: daphne config.asgi:application --bind 0.0.0.0 --port $DAPHNE_PORT
