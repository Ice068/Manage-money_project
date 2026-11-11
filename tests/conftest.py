import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import get_db
from app.main import create_app


@pytest.fixture
def client(tmp_path):
    test_database = tmp_path / "isolated-test.sqlite3"
    test_engine = create_engine(
        f"sqlite:///{test_database.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    test_session_local = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    test_app = create_app(database_engine=test_engine)

    def override_get_db():
        with test_session_local() as db:
            yield db

    test_app.dependency_overrides[get_db] = override_get_db

    with TestClient(test_app) as test_client:
        yield test_client

    test_app.dependency_overrides.clear()
    test_engine.dispose()
