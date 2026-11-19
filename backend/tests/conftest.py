from collections.abc import AsyncGenerator

import pytest
from app.core.config import settings
from app.db.session import get_db
from app.main import app
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

# Pastikan default testing berjalan offline dengan synthetic embeddings / fallback
settings.gemini_api_key = ""
settings.environment = "testing"

test_engine = create_async_engine(
    settings.database_url,
    poolclass=NullPool,
    future=True,
)

test_async_session_maker = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with test_async_session_maker() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db

from app.api import chat as chat_module
from app.db import session as session_module

session_module.async_session_maker = test_async_session_maker
chat_module.async_session_maker = test_async_session_maker


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
def mock_background_ingest_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    async def dummy_pipeline(paper_id: object) -> None:
        pass

    monkeypatch.setattr("app.api.papers.run_ingest_pipeline", dummy_pipeline)
