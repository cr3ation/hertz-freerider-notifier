from django import template

register = template.Library()

@register.filter
def get_item(d, key):
    try:
        return d.get(key, 0)
    except Exception:
        return ''
