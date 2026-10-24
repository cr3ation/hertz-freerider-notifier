from django import template
from django.utils.safestring import mark_safe

"""Custom template filters for scheduler app."""

register = template.Library()

# Outline icons (24x24, stroke based) used instead of emoji in the dashboard
ICONS = {
    'plus': '<path d="M5 12h14M12 5v14"/>',
    'bell': '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>',
    'car': '<path d="M7 17m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0"/><path d="M17 17m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0"/>'
           '<path d="M5 17h-2v-6l2 -5h9l4 5h1a2 2 0 0 1 2 2v4h-2m-4 0h-6m-6 -6h15m-6 0v-5"/>',
    'check': '<path d="M20 6 9 17l-5-5"/>',
    'refresh': '<path d="M21 12a9 9 0 1 1-3-6.7L21 8"/><path d="M21 3v5h-5"/>',
    'info': '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
    'list': '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
    'edit': '<path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/>',
    'trash': '<path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>',
}

@register.simple_tag
def route_marker(kind):
    """Grey ring for the origin, grey map pin for the destination: {% route_marker 'origin' %}"""
    if kind == 'origin':
        return mark_safe('<span class="rt-ico"><span class="ico-ring"></span></span>')
    return mark_safe(
        '<span class="rt-ico ico-pin"><svg width="15" height="17" viewBox="0 0 24 26" aria-hidden="true">'
        '<path d="M12 25s-8-7.4-8-14a8 8 0 0 1 16 0c0 6.6-8 14-8 14z" fill="currentColor"/>'
        '<circle cx="12" cy="11" r="3.2" fill="#fff"/></svg></span>'
    )

@register.simple_tag
def icon(name, size=16):
    """Inline SVG icon: {% icon 'bell' 18 %}"""
    return mark_safe(
        f'<svg class="ico" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS.get(name, "")}</svg>'
    )

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
