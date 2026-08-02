import os
import tempfile
import pytest

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["BRIEFING_DB_PATH"] = _tmp.name

from app.main import app
from app.database import init_db
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client():
    init_db()
    with TestClient(app) as c:
        yield c
    os.unlink(_tmp.name)


@pytest.fixture(autouse=True)
def clean_db():
    from app.database import get_db
    with get_db() as db:
        db.execute("DELETE FROM audit_events")
        db.execute("DELETE FROM reviews")
        db.execute("DELETE FROM attachments")
        db.execute("DELETE FROM findings")
        db.execute("DELETE FROM sites")
        db.execute("DELETE FROM templates")
        db.execute("DELETE FROM projects")
    yield
