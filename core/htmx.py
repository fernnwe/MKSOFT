from django.shortcuts import render


def htmx_render(request, template_name, context=None, base_template='base.html'):
    """
    Renderiza solo el contenido si es peticion HTMX, o el template completo si no.
    """
    if context is None:
        context = {}
    
    if request.htmx:
        # Para HTMX, renderizamos solo el bloque content
        context['htmx_request'] = True
        return render(request, template_name, context)
    else:
        # Para peticiones normales, usamos el base.html
        context['htmx_request'] = False
        return render(request, template_name, context)
