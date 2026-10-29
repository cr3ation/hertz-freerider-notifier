"""The map attached to notifications, drawn from (fake) OpenStreetMap tiles."""

import io

import requests
from django.core.cache import cache
from PIL import Image

from scheduler import routemap

YSTAD, GOTEBORG_C = (55.445249, 13.839516), (57.713142, 11.976078)


class FakeTiles:
    def __init__(self):
        self.urls = []

    def get(self, url, headers, timeout):
        self.urls.append((url, headers['User-Agent']))
        tile = io.BytesIO()
        Image.new('RGB', (256, 256), (200, 220, 240)).save(tile, 'PNG')
        response = requests.Response()
        response.status_code, response._content = 200, tile.getvalue()
        return response


def test_draws_a_jpeg_of_the_route(monkeypatch):
    tiles = FakeTiles()
    monkeypatch.setattr(requests, 'get', tiles.get)
    jpeg = routemap.render(YSTAD, GOTEBORG_C)
    image = Image.open(io.BytesIO(jpeg))
    assert (image.format, image.size) == ('JPEG', (routemap.WIDTH * routemap.SCALE, routemap.HEIGHT * routemap.SCALE))
    assert tiles.urls and all(url.startswith('https://tile.openstreetmap.org/') for url, _ in tiles.urls)
    assert all('hertz-freerider-notifier' in agent for _, agent in tiles.urls)  # OSM wants to know who asks
    # The tiles are kept, so the next map of the same area needs no downloads
    count = len(tiles.urls)
    routemap.render(YSTAD, GOTEBORG_C)
    assert len(tiles.urls) == count
    assert cache.get(tiles.urls[0][0].replace('https://tile.openstreetmap.org/', 'osm-tile:').removesuffix('.png'))


def test_gives_up_quietly_without_tiles():
    # The test setup blocks the network, so fetching tiles fails
    assert routemap.render(YSTAD, GOTEBORG_C) is None


def test_the_route_stays_in_the_middle_square():
    # iOS shows a square from the middle as the thumbnail
    zoom, stretch, cx, cy = routemap._fit([YSTAD, GOTEBORG_C], (66, 44, 66, 14))
    xs = [routemap._world(lat, lon, zoom)[0] for lat, lon in (YSTAD, GOTEBORG_C)]
    middle_square = routemap.HEIGHT / 2 / stretch
    assert all(abs(x - cx) <= middle_square for x in xs)
    assert 0.7 <= stretch <= 1.42
