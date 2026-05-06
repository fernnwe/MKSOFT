from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    if dictionary:
        return dictionary.get(key, key)
    return key


@register.filter
def attr(obj, name):
    return getattr(obj, name, False)
