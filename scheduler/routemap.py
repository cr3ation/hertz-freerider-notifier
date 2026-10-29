"""The map attached to a notification: grey OpenStreetMap tiles with the route drawn on top, in the same style
as the dashboard's route window (orange halo, dashed line, A and B pins).

OpenStreetMap's tile policy (https://operations.osmfoundation.org/policies/tiles/) asks for a User-Agent that
identifies the app, for cached tiles and for visible attribution. All three are done here.
"""

import io
import logging
import math

import requests
from django.core.cache import cache
from PIL import Image, ImageDraw, ImageFilter, ImageFont

logger = logging.getLogger(__name__)

TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
USER_AGENT = 'hertz-freerider-notifier (+https://github.com/cr3ation/hertz-freerider-notifier)'
TILE = 256
WIDTH, HEIGHT = 340, 260  # CSS pixels; the JPEG has SCALE times as many in each direction
SCALE = 2
SS = 4  # overlays are drawn at 4x and scaled down, which smooths lines, pins and text
# Pin gradient (left, right) and letter colour, as .pin-ab.a / .pin-ab.b in app.css
PINS = {'A': ((255, 179, 71), (255, 204, 51), (34, 34, 34)), 'B': ((255, 77, 77), (255, 153, 102), (255, 255, 255))}


def render(origin, destination):
    """JPEG bytes of a map from origin to destination, both (lat, lon), or None if it can't be drawn."""
    try:
        return _render(origin, destination)
    except Exception as e:  # a notification without a map beats no notification
        logger.warning('Could not draw the route map: %s', e)
        return None


def _render(origin, destination):
    # iOS shows a square from the middle of the image as the thumbnail, so the route is kept inside it
    side_pad = (WIDTH - min(WIDTH, HEIGHT)) / 2 + 26
    zoom, stretch, cx, cy = _fit([origin, destination], (side_pad, 44, side_pad, 14))
    image, (x0, y0) = _base_map(zoom, cx, cy, stretch)
    overlay = Image.new('RGBA', (WIDTH * SS, HEIGHT * SS))
    a, b = [
        ((x - x0) * stretch * SS, (y - y0) * stretch * SS) for x, y in (_world(*p, zoom) for p in (origin, destination))
    ]
    _route(overlay, a, b)
    _pin(overlay, a, 'A')
    _pin(overlay, b, 'B')
    _attribution(overlay)
    image = image.convert('RGBA')
    image.alpha_composite(overlay.resize(image.size, Image.LANCZOS))
    out = io.BytesIO()
    image.convert('RGB').save(out, 'JPEG', quality=85, optimize=True)
    return out.getvalue()


def _world(lat, lon, zoom):
    """Web Mercator pixel position of (lat, lon) in the whole world map at this zoom level."""
    size = TILE * 2**zoom
    sin = math.sin(math.radians(lat))
    return (lon + 180) / 360 * size, (0.5 - math.log((1 + sin) / (1 - sin)) / (4 * math.pi)) * size


def _fit(points, pad, max_zoom=13.0):
    """The zoom (fractional) that fits the points inside the image minus pad (left, top, right, bottom).

    Tiles only come in whole zoom levels, so this returns the nearest whole level, the stretch that makes up
    the difference (0.7-1.4) and the centre in that level's world pixels.
    """
    xs, ys = zip(*(_world(lat, lon, 0) for lat, lon in points), strict=True)
    zoom = max_zoom
    if max(xs) > min(xs):
        zoom = min(zoom, math.log2((WIDTH - pad[0] - pad[2]) / (max(xs) - min(xs))))
    if max(ys) > min(ys):
        zoom = min(zoom, math.log2((HEIGHT - pad[1] - pad[3]) / (max(ys) - min(ys))))
    whole = round(zoom)
    stretch, size = 2 ** (zoom - whole), 2**whole
    # The padding is in CSS pixels, the centre in the tile level's pixels
    cx = (min(xs) + max(xs)) / 2 * size + (pad[2] - pad[0]) / 2 / stretch
    cy = (min(ys) + max(ys)) / 2 * size + (pad[3] - pad[1]) / 2 / stretch
    return whole, stretch, cx, cy


def _tile(zoom, x, y):
    x %= 2**zoom
    key = f'osm-tile:{zoom}/{x}/{y}'
    data = cache.get(key)
    if data is None:
        resp = requests.get(TILE_URL.format(z=zoom, x=x, y=y), headers={'User-Agent': USER_AGENT}, timeout=10)
        resp.raise_for_status()
        data = resp.content
        cache.set(key, data, 7 * 24 * 3600)
    return Image.open(io.BytesIO(data)).convert('RGB')


def _base_map(zoom, cx, cy, stretch):
    """The tiles around (cx, cy), stretched and greyed like the dashboard map's CSS filter."""
    width, height = math.ceil(WIDTH / stretch), math.ceil(HEIGHT / stretch)
    x0, y0 = math.floor(cx - width / 2), math.floor(cy - height / 2)
    image = Image.new('RGB', (width, height), '#e5e5e5')
    for tx in range(x0 // TILE, (x0 + width - 1) // TILE + 1):
        for ty in range(y0 // TILE, (y0 + height - 1) // TILE + 1):
            if 0 <= ty < 2**zoom:
                image.paste(_tile(zoom, tx, ty), (tx * TILE - x0, ty * TILE - y0))
    # filter: grayscale(1) contrast(.92) brightness(1.04)
    grey = image.convert('L', (0.2126, 0.7152, 0.0722, 0))
    grey = grey.point(lambda v: max(0, min(255, round(((v / 255 - 0.5) * 0.92 + 0.5) * 1.04 * 255))))
    return grey.convert('RGB').resize((WIDTH * SCALE, HEIGHT * SCALE), Image.LANCZOS), (x0, y0)


def _layer(mask, rgb, opacity=1.0):
    layer = Image.new('RGBA', mask.size, rgb + (255,))
    layer.putalpha(mask if opacity == 1 else mask.point(lambda v: round(v * opacity)))
    return layer


def _route(overlay, a, b):
    """Orange halo plus a dark dashed line with round caps, like the route window's two polylines."""
    halo = Image.new('L', overlay.size)
    draw = ImageDraw.Draw(halo)
    width = 9 * SS
    draw.line([a, b], fill=255, width=width)
    for x, y in (a, b):
        draw.ellipse((x - width / 2, y - width / 2, x + width / 2, y + width / 2), fill=255)
    overlay.alpha_composite(_layer(halo, (255, 179, 71), 0.5))

    draw = ImageDraw.Draw(overlay)
    length = math.dist(a, b)
    width, dash, gap = 3 * SS, 8 * SS, 6 * SS
    dx, dy = ((b[0] - a[0]) / length, (b[1] - a[1]) / length) if length else (0, 0)
    start = 0.0
    while start < length:
        end = min(start + dash, length)
        p, q = (a[0] + dx * start, a[1] + dy * start), (a[0] + dx * end, a[1] + dy * end)
        draw.line([p, q], fill=(33, 37, 41, 255), width=width)
        for x, y in (p, q):
            draw.ellipse((x - width / 2, y - width / 2, x + width / 2, y + width / 2), fill=(33, 37, 41, 255))
        start += dash + gap


def _pin(overlay, tip, letter):
    """A teardrop pin with its point at tip: white rim, colour gradient, letter and a soft shadow."""
    left, right, ink = PINS[letter]
    cx, cy = tip[0], tip[1] - 21.2 * SS  # centre of the round part

    def shape(radius, point_y):
        mask = Image.new('L', overlay.size)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=255)
        side = radius * 0.7071  # where the point's edges meet the circle, at 45 degrees
        draw.polygon([(cx - side, cy + side), (cx + side, cy + side), (cx, point_y)], fill=255)
        return mask

    outer, inner = shape(15 * SS, tip[1]), shape(13 * SS, tip[1] - 2.83 * SS)
    shadow = outer.transform(outer.size, Image.AFFINE, (1, 0, 0, 0, 1, -3 * SS)).filter(
        ImageFilter.GaussianBlur(5 * SS)
    )
    overlay.alpha_composite(_layer(shadow, (0, 0, 0), 0.45))
    overlay.alpha_composite(_layer(outer, (255, 255, 255)))
    gradient = Image.linear_gradient('L').rotate(90).resize((round(26 * SS), overlay.height))
    colours = Image.composite(Image.new('RGB', gradient.size, right), Image.new('RGB', gradient.size, left), gradient)
    fill = Image.new('RGBA', overlay.size)
    fill.paste(colours, (round(cx - 13 * SS), 0))
    fill.putalpha(inner)
    overlay.alpha_composite(fill)
    font = ImageFont.load_default(size=13 * SS)
    ImageDraw.Draw(overlay).text(
        (cx, cy), letter, font=font, fill=ink, anchor='mm', stroke_width=SS // 2, stroke_fill=ink
    )


def _attribution(overlay):
    font = ImageFont.load_default(size=round(8.5 * SS))
    text = '© OpenStreetMap'
    width, height = font.getlength(text) + 8 * SS, 13 * SS
    x, y = overlay.width - width, overlay.height - height
    box = Image.new('RGBA', overlay.size)
    draw = ImageDraw.Draw(box)
    draw.rectangle((x, y, overlay.width, overlay.height), fill=(255, 255, 255, 204))
    draw.text((x + 4 * SS, y + height / 2), text, font=font, fill=(51, 51, 51, 255), anchor='lm')
    overlay.alpha_composite(box)
