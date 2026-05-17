from django.conf import settings


def restaurant_context(request):
    try:
        from core.models import ConfigRestaurante
        from facturacion.models import CajaApertura
        cliente = None
        if request.user.is_authenticated and hasattr(request.user, 'cliente'):
            cliente = request.user.cliente
        config = ConfigRestaurante.get_config(cliente)
        caja_abierta = None
        if request.user.is_authenticated:
            caja_qs = CajaApertura.objects.filter(estado=CajaApertura.Estado.ABIERTA)
            if cliente:
                caja_qs = caja_qs.filter(cliente=cliente)
            caja_abierta = caja_qs.first()
        return {
            "RESTAURANT_NAME": config.nombre,
            "RESTAURANT_RFC": config.rfc,
            "RESTAURANT_ADDRESS": config.direccion,
            "RESTAURANT_PHONE": config.telefono,
            "RESTAURANT_EMAIL": getattr(config, "email", ""),
            "CURRENCY_SYMBOL": config.simbolo_moneda,
            "TAX_RATE": config.tasa_impuesto,
            "PORCENTAJE_SERVICIO": config.porcentaje_servicio,
            "caja_abierta": caja_abierta,
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
            "PORCENTAJE_SERVICIO": settings.PORCENTAJE_SERVICIO,
            "caja_abierta": None,
        }
