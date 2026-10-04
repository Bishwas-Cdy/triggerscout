from collections.abc import AsyncGenerator

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.database import Base, get_db
from app.dependencies import get_classifier, get_scraper
from app.main import app
from app.services.classifier import TriggerClassifier
from app.services.llm import LLMClient


class FakeScraper:
    def __init__(self) -> None:
        self.responses: list[str] = []

    async def fetch(self, _: str) -> str:
        if not self.responses:
            raise AssertionError("No fake page response was queued")
        return self.responses.pop(0)


@pytest.fixture
def fake_scraper() -> FakeScraper:
    return FakeScraper()


@pytest_asyncio.fixture
async def client(fake_scraper: FakeScraper) -> AsyncGenerator[httpx.AsyncClient, None]:
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=test_engine, expire_on_commit=False)
    Base.metadata.create_all(test_engine)

    async def override_db() -> AsyncGenerator[Session, None]:
        with testing_session() as session:
            yield session

    async def override_scraper() -> FakeScraper:
        return fake_scraper

    async def override_classifier() -> TriggerClassifier:
        return TriggerClassifier(LLMClient(Settings(openai_api_key=None)))

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_scraper] = override_scraper
    app.dependency_overrides[get_classifier] = override_classifier
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(test_engine)
