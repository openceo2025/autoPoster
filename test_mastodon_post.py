import pytest
from fastapi.testclient import TestClient

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

def make_client(monkeypatch, config=None, mastodon_cls=None):
    if config is None:
        config = {
            'mastodon': {
                'accounts': {
                    'acc': {
                        'instance_url': 'https://mastodon.example',
                        'access_token': 'token'
                    }
                }
            }
        }
    monkeypatch.setattr(server, 'CONFIG', config, raising=False)
    if mastodon_cls:
        monkeypatch.setattr(server, 'Mastodon', mastodon_cls)
    server.MASTODON_CLIENTS = server.create_mastodon_clients()
    return TestClient(server.app)

def test_post_text(monkeypatch):
    dummy = DummyMastodon()
    client = make_client(monkeypatch, mastodon_cls=lambda **kw: dummy)
    resp = client.post('/mastodon/post', json={'account': 'acc', 'text': 'hello'})
    assert resp.status_code == 200
    assert resp.json() == {'posted': True}
    assert dummy.posts[0]['text'] == 'hello'
    assert dummy.posts[0]['media_ids'] is None
    assert dummy.media == []

def test_post_with_media(monkeypatch):
    dummy = DummyMastodon()
    client = make_client(monkeypatch, mastodon_cls=lambda **kw: dummy)
    resp = client.post('/mastodon/post', json={'account': 'acc', 'text': 'hi', 'media': ['abc']})
    assert resp.status_code == 200
    assert dummy.posts[0]['text'] == 'hi'
    assert dummy.media == ['abc']
    assert dummy.posts[0]['media_ids'] == [1]

def test_invalid_account(monkeypatch):
    dummy = DummyMastodon()
    client = make_client(monkeypatch, config={'mastodon': {'accounts': {}}}, mastodon_cls=lambda **kw: dummy)
    resp = client.post('/mastodon/post', json={'account': 'none', 'text': 'x'})
    assert resp.status_code == 200
    assert resp.json()['error'] == 'Account not configured'
    assert not dummy.posts
