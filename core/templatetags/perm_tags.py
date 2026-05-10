from django import template
from urllib.parse import urlencode, quote

register = template.Library()


@register.filter
def get_item(dictionary, key):
    if dictionary:
        return dictionary.get(key, key)
    return key


@register.filter
def attr(obj, name):
    return getattr(obj, name, False)


@register.filter
def remove(querystring, param_name):
    if not querystring:
        return ""
    parts = querystring.split("&")
    filtered = []
    for part in parts:
        if "=" in part:
            key = part.split("=")[0]
            if key not in (param_name, "page"):
                filtered.append(part)
        elif part not in (param_name, "page"):
            pass
    return "?" + "&".join(filtered) if filtered else ""
