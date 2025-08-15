from django import template

"""Custom template filters for scheduler app."""

register = template.Library()

@register.filter
def get_item(d, key):
    try:
        return d.get(key, 0)
    except Exception:
        return ''

@register.filter(name='add_class')
def add_class(field, css):
    """Add CSS class(es) to a Django form field widget in templates.

    Usage: {{ form.field|add_class:"form-control" }}
    Supports multiple classes separated by spaces and preserves existing ones.
    """
    try:
        existing = field.field.widget.attrs.get('class', '')
        classes = f"{existing} {css}".strip() if existing else css
        field.field.widget.attrs['class'] = classes
        return field
    except Exception:
        return field
