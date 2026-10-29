from django import template
from django.templatetags.static import static
from django.utils.html import format_html
from django.utils.safestring import mark_safe

"""Custom template filters for scheduler app."""

register = template.Library()


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
def airport_icon(is_airport):
    """Small grey plane after airport names: {% airport_icon r.destination.airport %}"""
    return mark_safe(f'<span class="ico-plane" title="Airport">{icon("plane", 14)}</span>') if is_airport else ''


@register.simple_tag
def icon(name, size=16):
    """Outline icon from the sprite static/scheduler/icons.svg: {% icon 'bell' 18 %}"""
    return format_html(
        '<svg class="ico" width="{0}" height="{0}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<use href="{1}#{2}"></use></svg>',
        size,
        static('scheduler/icons.svg'),
        name,
    )


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
