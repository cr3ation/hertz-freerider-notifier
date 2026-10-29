"""Shared fixtures. Tests never reach the network: Hertz and Pushover calls must be mocked."""

import json
from pathlib import Path

import pytest
import requests

FIXTURES = Path(__file__).parent / 'fixtures'


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError('Tests must not make real HTTP requests; mock the call instead')

    monkeypatch.setattr(requests, 'get', blocked)
    monkeypatch.setattr(requests, 'post', blocked)
    # .env may hold real Pushover credentials; a test must never pick them up
    monkeypatch.delenv('PUSHOVER_USER', raising=False)
    monkeypatch.delenv('PUSHOVER_TOKEN', raising=False)


@pytest.fixture
def transport_routes():
    """A real response from /api/transport-routes/ (August 2025, 95 routes)."""
    return json.loads((FIXTURES / 'transport_routes.json').read_text(encoding='utf-8'))


@pytest.fixture
def locations():
    """A real response from /api/locations/ (231 stations)."""
    return json.loads((FIXTURES / 'locations.json').read_text(encoding='utf-8'))
