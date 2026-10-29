"""The outline icons come from one sprite, static/scheduler/icons.svg, for the templates and the JavaScript alike."""

import re
from pathlib import Path

from scheduler.templatetags.scheduler_extras import icon

APP = Path(__file__).resolve().parent.parent
SPRITE = APP / 'static' / 'scheduler' / 'icons.svg'
# Icons the JavaScript picks at run time: the car or a van, the battery badge and the info lines' icons
JS_DYNAMIC = {'car', 'bus', 'bolt', 'plug', 'key', 'parking', 'door', 'info'}


def test_icon_tag_uses_the_sprite():
    html = icon('bell', 18)
    assert html.startswith('<svg class="ico" width="18" height="18" viewBox="0 0 24 24"')
    assert '<use href="/static/scheduler/icons.svg#bell"></use>' in html


def test_every_icon_in_use_is_in_the_sprite():
    symbols = set(re.findall(r'<symbol id="([\w-]+)"', SPRITE.read_text(encoding='utf-8')))
    templates = ''.join(p.read_text(encoding='utf-8') for p in (APP / 'templates').rglob('*.html'))
    scripts = ''.join(p.read_text(encoding='utf-8') for p in (APP / 'static').rglob('*.js'))
    used = (
        set(re.findall(r"{% icon '([\w-]+)'", templates)) | set(re.findall(r"icon\('([\w-]+)'", scripts)) | JS_DYNAMIC
    )
    used.add('plane')  # {% airport_icon %}
    assert used <= symbols, f'missing from icons.svg: {sorted(used - symbols)}'
    assert symbols <= used, f'unused in icons.svg: {sorted(symbols - used)}'
