import os
import sys
import pytest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.database import Base, get_db
from app.main import app
import app.routers.jobs as jobs_router


@pytest.fixture(scope="function")
def setup_test_env(tmp_path: Path):
    db_file = tmp_path / "test_app.db"
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    db_url = f"sqlite:///{db_file}"
    orig_db_url = settings.DATABASE_URL
    orig_output_dir = settings.OUTPUT_DIR
    settings.DATABASE_URL = db_url
    settings.OUTPUT_DIR = str(output_dir)
    test_engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    orig_router_sessionlocal = jobs_router.SessionLocal
    jobs_router.SessionLocal = TestingSessionLocal
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    app.dependency_overrides[get_db] = override_get_db
    yield {
        "db_engine": test_engine,
        "session_factory": TestingSessionLocal,
        "output_dir": output_dir,
    }
    app.dependency_overrides.clear()
    jobs_router.SessionLocal = orig_router_sessionlocal
    settings.DATABASE_URL = orig_db_url
    settings.OUTPUT_DIR = orig_output_dir

@pytest.fixture(scope="function")
def client(setup_test_env):
    with TestClient(app) as test_client:
        yield test_client
