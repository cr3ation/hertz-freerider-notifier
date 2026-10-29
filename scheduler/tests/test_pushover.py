"""send_pushover tells the caller whether Pushover accepted the message, so a failed send is never counted as sent."""

from types import SimpleNamespace

import pytest
import requests

from scheduler.pushover import send as send_pushover


@pytest.fixture
def credentials(monkeypatch):
    monkeypatch.setenv('PUSHOVER_USER', 'test-user')
    monkeypatch.setenv('PUSHOVER_TOKEN', 'test-token')


def fake_post(status=200, body='{"status":1}', error=None, calls=None):
    def post(url, data, files, timeout):
        if calls is not None:
            calls.append(SimpleNamespace(url=url, data=data, files=files, timeout=timeout))
        if error:
            raise error
        response = requests.Response()
        response.status_code, response._content, response.url = status, body.encode(), url
        return response

    return post


def test_accepted_message(monkeypatch, credentials):
    calls = []
    monkeypatch.setattr(requests, 'post', fake_post(calls=calls))
    assert send_pushover('<b>Hi</b>', title='Test', url='https://example.com', url_title='Open', html=True) is True
    [call] = calls
    assert call.url == 'https://api.pushover.net/1/messages.json'
    assert call.data == {
        'token': 'test-token',
        'user': 'test-user',
        'message': '<b>Hi</b>',
        'title': 'Test',
        'priority': 0,
        'url': 'https://example.com',
        'url_title': 'Open',
        'html': 1,
    }
    assert call.files is None


def test_sends_the_image_as_an_attachment(monkeypatch, credentials):
    calls = []
    monkeypatch.setattr(requests, 'post', fake_post(calls=calls))
    assert send_pushover('Hi', image=b'jpeg-bytes') is True
    assert calls[0].files == {'attachment': ('route.jpg', b'jpeg-bytes', 'image/jpeg')}


def test_rejected_message(monkeypatch, credentials, caplog):
    monkeypatch.setattr(requests, 'post', fake_post(400, '{"errors":["application token is invalid"],"status":0}'))
    assert send_pushover('Hi') is False
    assert 'application token is invalid' in caplog.text


def test_pushover_unreachable(monkeypatch, credentials):
    monkeypatch.setattr(requests, 'post', fake_post(error=requests.ConnectionError('timeout')))
    assert send_pushover('Hi') is False


def test_not_configured(monkeypatch):
    calls = []
    monkeypatch.setattr(requests, 'post', fake_post(calls=calls))
    assert send_pushover('Hi') is False
    assert calls == []
