import json
import base64
from io import BytesIO

import pytest
from fastapi.testclient import TestClient

import server


class DummyAPI:
    def __init__(self, *args, **kwargs):
        self.media = []
        self.next_id = 1

    def verify_credentials(self):
        return type('User', (), {'screen_name': 'dummyuser'})()

    def media_upload(self, filename=None, file=None):
        self.media.append(file)
        mid = self.next_id
        self.next_id += 1
        obj = type('Upload', (), {})()
        obj.media_id = mid
        return obj


class DummyClient:
    def __init__(self, *args, **kwargs):
        self.tweets = []

    def create_tweet(self, text=None, media_ids=None):
        self.tweets.append({'text': text, 'media_ids': media_ids})
        return type('Resp', (), {'data': {'id': '1'}})()


@pytest.fixture
def tw_config_writer(tmp_path, monkeypatch):
    """Return a helper to write a config file and load it into the server."""

    def _write(cfg):
        cfg_path = tmp_path / 'config.json'
        cfg_path.write_text(json.dumps(cfg))
        monkeypatch.setattr(server, 'CONFIG_PATH', cfg_path, raising=False)
        with cfg_path.open() as fh:
            server.CONFIG = json.load(fh)
        return cfg_path

    return _write


@pytest.fixture
def tw_temp_config(tw_config_writer):
    """Write a valid config.json and ensure the server loads it."""
    cfg = {
        'twitter': {
            'accounts': {
                'acc': {
                    'consumer_key': 'ck',
                    'consumer_secret': 'cs',
                    'access_token': 'at',
                    'access_token_secret': 'ats',
                    'bearer_token': 'bt',
                }
            }
        }
    }
    return tw_config_writer(cfg)


def make_client(monkeypatch, config=None, client_cls=None, api_cls=None):
    if config is not None:
        monkeypatch.setattr(server, 'CONFIG', config, raising=False)
    if client_cls:
        monkeypatch.setattr(server.tweepy, 'Client', client_cls)
    if api_cls:
        monkeypatch.setattr(server.tweepy, 'API', api_cls)
    monkeypatch.setattr(server.tweepy, 'OAuth1UserHandler', lambda *a, **kw: None)
    server.TWITTER_ACCOUNT_ERRORS = server.validate_twitter_accounts(server.CONFIG)
    server.TWITTER_CLIENTS = server.create_twitter_clients()
    return TestClient(server.app)


def test_post_text(monkeypatch, tw_temp_config):
    dummy_api = DummyAPI()
    dummy_client = DummyClient()
    client = make_client(
        monkeypatch,
        client_cls=lambda **kw: dummy_client,
        api_cls=lambda auth: dummy_api,
    )
    resp = client.post('/twitter/post', json={'account': 'acc', 'text': 'hello'})
    assert resp.status_code == 200
    assert resp.json() == {
        'id': '1',
        'link': 'https://twitter.com/dummyuser/status/1',
        'site': 'twitter'
    }
    assert dummy_client.tweets[0]['text'] == 'hello'
    assert dummy_client.tweets[0]['media_ids'] is None
    assert dummy_api.media == []


def test_post_with_media(monkeypatch, tw_temp_config):
    dummy_api = DummyAPI()
    dummy_client = DummyClient()
    client = make_client(
        monkeypatch,
        client_cls=lambda **kw: dummy_client,
        api_cls=lambda auth: dummy_api,
    )
    data = b'imgdata'
    encoded = base64.b64encode(data).decode()
    resp = client.post('/twitter/post', json={'account': 'acc', 'text': 'hi', 'media': [encoded]})
    assert resp.status_code == 200
    assert resp.json() == {
        'id': '1',
        'link': 'https://twitter.com/dummyuser/status/1',
        'site': 'twitter'
    }
    assert dummy_client.tweets[0]['text'] == 'hi'
    assert isinstance(dummy_api.media[0], BytesIO)
    assert dummy_api.media[0].read() == data
    assert dummy_client.tweets[0]['media_ids'] == [1]


def test_invalid_account(monkeypatch, tw_temp_config):
    dummy_api = DummyAPI()
    dummy_client = DummyClient()
    client = make_client(
        monkeypatch,
        config={'twitter': {'accounts': {}}},
        client_cls=lambda **kw: dummy_client,
        api_cls=lambda auth: dummy_api,
    )
    resp = client.post('/twitter/post', json={'account': 'none', 'text': 'x'})
    assert resp.status_code == 200
    assert resp.json()['error'] == 'Account not configured'
    assert not dummy_client.tweets


def test_misconfigured_account(monkeypatch, tw_temp_config):
    cfg = {
        'twitter': {
            'accounts': {
                'acc': {
                    'consumer_key': 'YOUR_CONSUMER_KEY',
                    'consumer_secret': 'YOUR_CONSUMER_SECRET',
                    'access_token': 'YOUR_ACCESS_TOKEN',
                    'access_token_secret': 'YOUR_ACCESS_TOKEN_SECRET',
                    'bearer_token': 'YOUR_BEARER_TOKEN',
                }
            }
        }
    }
    dummy_api = DummyAPI()
    dummy_client = DummyClient()
    client = make_client(
        monkeypatch,
        config=cfg,
        client_cls=lambda **kw: dummy_client,
        api_cls=lambda auth: dummy_api,
    )
    resp = client.post('/twitter/post', json={'account': 'acc', 'text': 'x'})
    assert resp.status_code == 200
    assert resp.json()['error'] == 'Account misconfigured'
    assert not dummy_client.tweets


@pytest.fixture
def tw_empty_accounts_config(tw_config_writer):
    """Config with an empty twitter.accounts section."""
    cfg = {'twitter': {'accounts': {}}}
    return tw_config_writer(cfg)


@pytest.fixture(params=[
    {'twitter': {'accounts': {'acc': {'consumer_key': 'ck'}}}},
    {'twitter': {'accounts': {'acc': {'access_token': 'at'}}}},
    {'twitter': {'accounts': {'acc': {
        'consumer_key': 'ck', 'consumer_secret': 'cs', 'access_token': 'at',
        'access_token_secret': 'ats', 'bearer_token': 'YOUR_BEARER_TOKEN'}}}},
    {'twitter': {'accounts': {'acc': {
        'consumer_key': 'YOUR_CONSUMER_KEY', 'consumer_secret': 'cs',
        'access_token': 'at', 'access_token_secret': 'ats', 'bearer_token': 'bt'}}}},
])
def tw_misconfigured_cfg(tw_config_writer, request):
    """Return various misconfigured account setups."""
    return tw_config_writer(request.param)


def test_accounts_empty(monkeypatch, tw_empty_accounts_config):
    dummy_api = DummyAPI()
    dummy_client = DummyClient()
    client = make_client(
        monkeypatch,
        client_cls=lambda **kw: dummy_client,
        api_cls=lambda auth: dummy_api,
    )
    resp = client.post('/twitter/post', json={'account': 'acc', 'text': 'x'})
    assert resp.status_code == 200
    assert resp.json()['error'] == 'Account not configured'
    assert not dummy_client.tweets


def test_account_missing_or_placeholder(monkeypatch, tw_misconfigured_cfg):
    dummy_api = DummyAPI()
    dummy_client = DummyClient()
    client = make_client(
        monkeypatch,
        client_cls=lambda **kw: dummy_client,
        api_cls=lambda auth: dummy_api,
    )
    resp = client.post('/twitter/post', json={'account': 'acc', 'text': 'x'})
    assert resp.status_code == 200
    assert resp.json()['error'] == 'Account misconfigured'
    assert not dummy_client.tweets
