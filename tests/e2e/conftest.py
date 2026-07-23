import asyncio
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import app.db.models  # noqa: F401
import app.db.session as db_session
import app.shared.infrastructure.dependencies as dependencies
from app.core.config import settings
from app.db.base import Base
from app.main import app
from app.modules.auth.infrastructure.models.user import UserModel

TEST_DATABASE_URL = (
    make_url(settings.database_url)
    .set(
        username="el_bisne_test",
        password="el_bisne_test",
        database="el_bisne_test",
    )
    .render_as_string(hide_password=False)
)
test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
test_session_factory = async_sessionmaker(test_engine, expire_on_commit=False)


def run_async(coroutine: object) -> object:
    return asyncio.run(coroutine)  # type: ignore[arg-type]


async def reset_database() -> None:
    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    await test_engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def isolated_e2e_database() -> Iterator[None]:
    original_db_factory = db_session.async_session_factory
    original_dependency_factory = dependencies.async_session_factory
    db_session.async_session_factory = test_session_factory
    dependencies.async_session_factory = test_session_factory
    run_async(reset_database())
    yield
    run_async(reset_database())
    db_session.async_session_factory = original_db_factory
    dependencies.async_session_factory = original_dependency_factory


@pytest.fixture(autouse=True)
def clean_database() -> Iterator[None]:
    run_async(reset_database())
    yield


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def register_and_login(
    client: TestClient, email: str, password: str = "strong-password"
) -> tuple[dict[str, object], dict[str, str]]:
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": email.split("@")[0]},
    )
    assert register_response.status_code == 201, register_response.text
    login_response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login_response.status_code == 200, login_response.text
    tokens = login_response.json()
    return tokens, {"Authorization": f"Bearer {tokens['access_token']}"}


async def make_platform_admin(email: str) -> None:
    async with test_session_factory() as session:
        await session.execute(
            update(UserModel).where(UserModel.email == email).values(is_platform_admin=True)
        )
        await session.commit()
