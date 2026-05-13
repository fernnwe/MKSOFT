from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags


def enviar_email_bienvenida(cliente, password):
    context = {
        "system_name": "Mi Restaurante",
        "system_email": settings.DEFAULT_FROM_EMAIL,
        "admin_name": "Administrador",
        "restaurant_name": cliente.nombre_negocio,
        "username": cliente.admin_username,
        "password": password,
        "login_url": settings.SITE_URL + "/cliente/login/",
        "plan": "Unico",
        "periodo": {
            "14": "14 dias (Prueba)",
            "30": "30 dias (Mensual)",
            "90": "90 dias (Trimestral)",
            "180": "180 dias (Semestral)",
            "365": "365 dias (Anual)",
        }.get(cliente.periodo_dias or "30", "30 dias"),
        "fecha_pago": cliente.fecha_pago_proximo.strftime("%d/%m/%Y") if cliente.fecha_pago_proximo else "N/A",
    }

    html_content = render_to_string("core/emails/bienvenida.html", context)
    text_content = strip_tags(html_content)

    msg = EmailMultiAlternatives(
        subject=f"Bienvenido a {context['system_name']} - Credenciales de acceso",
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[cliente.admin_email] if cliente.admin_email else [settings.DEFAULT_FROM_EMAIL],
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()
