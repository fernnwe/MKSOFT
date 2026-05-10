from django.conf import settings


def restaurant_context(request):
    try:
        from core.models import ConfigRestaurante
        cliente = None
        if request.user.is_authenticated and hasattr(request.user, 'cliente'):
            cliente = request.user.cliente
        config = ConfigRestaurante.get_config(cliente)
        return {
            "RESTAURANT_NAME": config.nombre,
            "RESTAURANT_RFC": config.rfc,
            "RESTAURANT_ADDRESS": config.direccion,
            "RESTAURANT_PHONE": config.telefono,
            "RESTAURANT_EMAIL": getattr(config, "email", ""),
            "CURRENCY_SYMBOL": config.simbolo_moneda,
            "TAX_RATE": config.tasa_impuesto,
        }
    except Exception:
        return {
            "RESTAURANT_NAME": settings.RESTAURANT_NAME,
            "RESTAURANT_RFC": settings.RESTAURANT_RFC,
            "RESTAURANT_ADDRESS": settings.RESTAURANT_ADDRESS,
            "RESTAURANT_PHONE": settings.RESTAURANT_PHONE,
            "RESTAURANT_EMAIL": "",
            "CURRENCY_SYMBOL": settings.CURRENCY_SYMBOL,
            "TAX_RATE": settings.TAX_RATE,
        }
