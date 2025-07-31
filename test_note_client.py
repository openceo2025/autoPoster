import requests
import pytest
from note_client import NoteClient, NoteAuthError

class DummySession:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self.json_data = json_data or {}
        self.post_args = []
        self.cookies = requests.cookies.RequestsCookieJar()

    def post(self, url, data=None, files=None, **kwargs):
        self.post_args.append((url, data, files))
        resp = type('Resp', (), {})()
        resp.status_code = self.status_code
        resp.cookies = requests.cookies.RequestsCookieJar()
        resp.cookies.set('sid', 'cookie')
        def raise_for_status():
            if resp.status_code >= 400:
                raise requests.HTTPError(resp.status_code)
        resp.raise_for_status = raise_for_status
        def json_func():
            return self.json_data
        resp.json = json_func
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


def test_upload_image_success(tmp_path):
    cfg = {'note': {'base_url': 'http://host'}}
    session = DummySession(200, json_data={'url': 'http://cdn/x.png'})
    client = NoteClient(cfg, session=session)
    img = tmp_path / 'img.txt'
    img.write_text('data')
    url = client.upload_image(img)
    assert url == 'http://cdn/x.png'
    assert session.post_args[0][0] == 'http://host/api/v1/upload_image'
    assert 'file' in session.post_args[0][2]


def test_upload_image_failure(tmp_path):
    cfg = {'note': {'base_url': 'http://host'}}
    session = DummySession(500)
    client = NoteClient(cfg, session=session)
    img = tmp_path / 'img.txt'
    img.write_text('data')
    with pytest.raises(RuntimeError):
        client.upload_image(img)
