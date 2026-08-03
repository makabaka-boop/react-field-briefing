import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")

    import importlib

    from app.core import database as db_module
    from app.core.config import settings

    db_module.engine.dispose()
    db_module.engine = db_module.create_engine(
        settings.DATABASE_URL, connect_args={"check_same_thread": False}, future=True
    )
    db_module.SessionLocal.configure(bind=db_module.engine)
    db_module.Base.metadata.drop_all(bind=db_module.engine)
    db_module.init_db()

    import app.main as main_module
    importlib.reload(main_module)
    from app.main import app

    with TestClient(app) as c:
        yield c

    db_module.Base.metadata.drop_all(bind=db_module.engine)
    db_module.engine.dispose()
