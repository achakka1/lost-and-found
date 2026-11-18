import os
import sys
import tempfile

import pytest

# Point the app at a throwaway database before it is imported.
_tmp = tempfile.mkdtemp()
os.environ["DB_PATH"] = os.path.join(_tmp, "import.db")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import app as app_module  # noqa: E402
from seed import seed  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A test client backed by a fresh, seeded SQLite file for each test."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(app_module, "DB_PATH", db_path)
    app_module.init_db()
    seed(db_path)
    app_module.app.config.update(TESTING=True)
    with app_module.app.test_client() as c:
        yield c


def login(client, username="alice", password="password123"):
    return client.post("/login", data={"username": username, "password": password},
                       follow_redirects=True)
