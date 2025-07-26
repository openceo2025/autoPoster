import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"

if not CONFIG_PATH.exists():
    pytest.fail("config.json not found. Please create it with Mastodon account information before running tests.")
else:
    with CONFIG_PATH.open() as fh:
        _cfg = json.load(fh)
    if not _cfg.get("mastodon", {}).get("accounts"):
        pytest.fail("No Mastodon accounts configured in config.json.")

import server

class DummyMastodon:
    def __init__(self, *args, **kwargs):
        self.init_args = kwargs
        self.posts = []
        self.media = []
        self.next_id = 1

    def status_post(self, text, media_ids=None):
        self.posts.append({'text': text, 'media_ids': media_ids})
        return {'id': 1}

    def media_post(self, data):
        self.media.append(data)
        mid = self.next_id
        self.next_id += 1
        return {'id': mid}


@pytest.fixture
def config_writer(tmp_path, monkeypatch):
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
def temp_config(config_writer):
    """Write a valid config.json and ensure the server loads it."""
    cfg = {
        'mastodon': {
            'accounts': {
                'acc': {
                    'instance_url': 'https://mastodon.social',
                    'access_token': 'token'
                }
            }
        }
    }
    return config_writer(cfg)

def make_client(monkeypatch, config=None, mastodon_cls=None):
    if config is not None:
        monkeypatch.setattr(server, 'CONFIG', config, raising=False)
    if mastodon_cls:
        monkeypatch.setattr(server, 'Mastodon', mastodon_cls)
    server.MASTODON_ACCOUNT_ERRORS = server.validate_mastodon_accounts(server.CONFIG)
    server.MASTODON_CLIENTS = server.create_mastodon_clients()
    return TestClient(server.app)

def test_post_text(monkeypatch, temp_config):
    dummy = DummyMastodon()
    client = make_client(monkeypatch, mastodon_cls=lambda **kw: dummy)
    resp = client.post('/mastodon/post', json={'account': 'acc', 'text': 'hello'})
    assert resp.status_code == 200
    assert resp.json() == {'posted': True}
    assert dummy.posts[0]['text'] == 'hello'
    assert dummy.posts[0]['media_ids'] is None
    assert dummy.media == []

def test_post_with_media(monkeypatch, temp_config):
    dummy = DummyMastodon()
    client = make_client(monkeypatch, mastodon_cls=lambda **kw: dummy)
    resp = client.post('/mastodon/post', json={'account': 'acc', 'text': 'hi', 'media': ['abc']})
    assert resp.status_code == 200
    assert dummy.posts[0]['text'] == 'hi'
    assert dummy.media == ['abc']
    assert dummy.posts[0]['media_ids'] == [1]

def test_invalid_account(monkeypatch, temp_config):
    dummy = DummyMastodon()
    client = make_client(monkeypatch, config={'mastodon': {'accounts': {}}}, mastodon_cls=lambda **kw: dummy)
    resp = client.post('/mastodon/post', json={'account': 'none', 'text': 'x'})
    assert resp.status_code == 200
    assert resp.json()['error'] == 'Account not configured'
    assert not dummy.posts


def test_misconfigured_account(monkeypatch, temp_config):
    cfg = {
        'mastodon': {
            'accounts': {
                'acc': {
                    'instance_url': 'https://mastodon.example',
                    'access_token': 'YOUR_TOKEN',
                }
            }
        }
    }
    dummy = DummyMastodon()
    client = make_client(monkeypatch, config=cfg, mastodon_cls=lambda **kw: dummy)
    resp = client.post('/mastodon/post', json={'account': 'acc', 'text': 'x'})
    assert resp.status_code == 200
    assert resp.json()['error'] == 'Account misconfigured'
    assert not dummy.posts


@pytest.fixture
def empty_accounts_config(config_writer):
    """Config with an empty mastodon.accounts section."""
    cfg = {'mastodon': {'accounts': {}}}
    return config_writer(cfg)


@pytest.fixture(params=[
    {'mastodon': {'accounts': {'acc': {'instance_url': 'https://mastodon.social'}}}},
    {'mastodon': {'accounts': {'acc': {'access_token': 'token'}}}},
    {'mastodon': {'accounts': {'acc': {'instance_url': 'https://mastodon.social', 'access_token': 'YOUR_TOKEN'}}}},
    {'mastodon': {'accounts': {'acc': {'instance_url': 'https://mastodon.example', 'access_token': 'token'}}}},
])
def misconfigured_cfg(config_writer, request):
    """Return various misconfigured account setups."""
    return config_writer(request.param)


def test_accounts_empty(monkeypatch, empty_accounts_config):
    dummy = DummyMastodon()
    client = make_client(monkeypatch, mastodon_cls=lambda **kw: dummy)
    resp = client.post('/mastodon/post', json={'account': 'acc', 'text': 'x'})
    assert resp.status_code == 200
    assert resp.json()['error'] == 'Account not configured'
    assert not dummy.posts


def test_account_missing_or_placeholder(monkeypatch, misconfigured_cfg):
    dummy = DummyMastodon()
    client = make_client(monkeypatch, mastodon_cls=lambda **kw: dummy)
    resp = client.post('/mastodon/post', json={'account': 'acc', 'text': 'x'})
    assert resp.status_code == 200
    assert resp.json()['error'] == 'Account misconfigured'
    assert not dummy.posts

