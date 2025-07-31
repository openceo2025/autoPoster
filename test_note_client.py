import requests
import pytest
from note_client import NoteClient, NoteAuthError

class DummySession:
    def __init__(self, status_code=200):
        self.status_code = status_code
        self.post_args = []
        self.cookies = requests.cookies.RequestsCookieJar()

    def post(self, url, data=None, **kwargs):
        self.post_args.append((url, data))
        resp = type('Resp', (), {})()
        resp.status_code = self.status_code
        resp.cookies = requests.cookies.RequestsCookieJar()
        resp.cookies.set('sid', 'cookie')
        # mimic requests.Session behavior updating cookies
        self.cookies.update(resp.cookies)
        return resp

def test_login_success():
    cfg = {'note': {'username': 'u', 'password': 'p', 'base_url': 'http://host'}}
    session = DummySession(200)
    client = NoteClient(cfg, session=session)
    client.login()
    assert session.post_args[0][0] == 'http://host/api/v1/sessions/sign_in'
    assert session.post_args[0][1] == {'login': 'u', 'password': 'p'}
    assert session.cookies.get('sid') == 'cookie'

def test_login_failure():
    cfg = {'note': {'username': 'u', 'password': 'p', 'base_url': 'http://host'}}
    session = DummySession(401)
    client = NoteClient(cfg, session=session)
    with pytest.raises(NoteAuthError):
        client.login()
