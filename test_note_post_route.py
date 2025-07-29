import json
import server
from fastapi.testclient import TestClient
import pytest

class DummyElement:
    def send_keys(self, *args, **kwargs):
        pass
    def clear(self):
        pass
    def click(self):
        pass
    def is_enabled(self):
        return True

class DummyDriver:
    def __init__(self, fail=None, *args, **kwargs):
        self.fail = fail
        self.actions = []
    def get(self, url):
        self.actions.append(('get', url))
    def find_element(self, by, selector, *args, **kwargs):
        self.actions.append(('find', selector))
        if selector == self.fail:
            raise Exception('missing')
        return DummyElement()
    def save_screenshot(self, path):
        self.actions.append(('screenshot', path))
        with open(path, 'wb') as fh:
            fh.write(b'')
    def quit(self):
        self.actions.append(('quit',))

class DummyWait:
    def __init__(self, driver, timeout):
        pass
    def until(self, condition):
        return True

@pytest.fixture
def note_config_writer(tmp_path, monkeypatch):
    def _write(cfg):
        cfg_path = tmp_path / 'config.json'
        cfg_path.write_text(json.dumps(cfg))
        monkeypatch.setattr(server, 'CONFIG_PATH', cfg_path, raising=False)
        with cfg_path.open() as fh:
            server.CONFIG = json.load(fh)
        return cfg_path
    return _write

@pytest.fixture
def note_temp_config(note_config_writer):
    cfg = {
        'note': {
            'accounts': {
                'acc': {
                    'username': 'user',
                    'password': 'pass',
                }
            }
        }
    }
    return note_config_writer(cfg)


def make_client(monkeypatch, config=None):
    if config is not None:
        monkeypatch.setattr(server, 'CONFIG', config, raising=False)
    server.NOTE_ACCOUNT_ERRORS = server.validate_note_accounts(server.CONFIG)
    server.NOTE_ACCOUNTS = server.load_note_accounts()
    return TestClient(server.app)


def patch_driver(monkeypatch, fail_selector=None):
    monkeypatch.setattr(server.webdriver, 'Chrome', lambda *a, **kw: DummyDriver(fail_selector))
    monkeypatch.setattr(server, 'WebDriverWait', lambda driver, timeout: DummyWait(driver, timeout))
    import tempfile
    def fake_temp(data, suffix=''):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.close()
        return tmp.name
    monkeypatch.setattr(server, '_temp_file_from_b64', fake_temp)


def test_note_post_success(monkeypatch, note_temp_config):
    patch_driver(monkeypatch)
    client = make_client(monkeypatch)
    payload = {
        'account': 'acc',
        'text': 'hello',
        'media': ['m1'],
        'thumbnail': 'th',
        'paid': False,
        'tags': ['t']
    }
    resp = client.post('/note/post', json=payload)
    assert resp.status_code == 200
    assert resp.json() == {'posted': True}


def test_note_post_misconfigured(monkeypatch, note_config_writer):
    cfg = {
        'note': {
            'accounts': {
                'acc': {
                    'username': 'your_username',
                    'password': 'your_password',
                }
            }
        }
    }
    note_config_writer(cfg)
    patch_driver(monkeypatch)
    client = make_client(monkeypatch)
    payload = {'account': 'acc', 'text': 'x', 'paid': False}
    resp = client.post('/note/post', json=payload)
    assert resp.status_code == 200
    assert resp.json()['error'] == 'Account misconfigured'


def test_note_post_login_error(monkeypatch, note_temp_config):
    fail = server.NOTE_SELECTORS['login_username']
    patch_driver(monkeypatch, fail_selector=fail)
    client = make_client(monkeypatch)
    payload = {'account': 'acc', 'text': 'x', 'paid': False}
    resp = client.post('/note/post', json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data['error'].startswith('login failed')
    assert 'screenshot' in data


def test_note_post_publish_error(monkeypatch, note_temp_config):
    fail = server.NOTE_SELECTORS['publish']
    patch_driver(monkeypatch, fail_selector=fail)
    client = make_client(monkeypatch)
    payload = {'account': 'acc', 'text': 'x', 'paid': False}
    resp = client.post('/note/post', json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data['error'].startswith('publish failed')
    assert 'screenshot' in data
