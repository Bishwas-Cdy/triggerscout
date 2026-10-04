from typing import Any

import httpx
import pytest

from app.dependencies import get_classifier
from app.main import app
from app.services.classifier import TriggerClassifier
from app.services.diff import ChangeCandidate
from app.services.llm import LLMError
from tests.conftest import FakeScraper


async def create_company(client: httpx.AsyncClient) -> int:
    response = await client.post(
        "/companies",
        json={
            "name": "Acme",
            "website": "https://example.com",
            "pages_to_monitor": ["https://example.com/news"],
        },
    )
    assert response.status_code == 201
    return int(response.json()["id"])


@pytest.mark.asyncio
async def test_health(client: httpx.AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_company_creation_and_get(client: httpx.AsyncClient) -> None:
    company_id = await create_company(client)
    response = await client.get(f"/companies/{company_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Acme"


@pytest.mark.asyncio
async def test_initial_snapshot_has_no_change(
    client: httpx.AsyncClient, fake_scraper: FakeScraper
) -> None:
    company_id = await create_company(client)
    fake_scraper.responses = ["<main>We help startups manage sales.</main>"]
    response = await client.post(f"/companies/{company_id}/scan")
    assert response.status_code == 200
    body = response.json()
    assert body["results"][0]["result"]["trigger"] == "NO_MEANINGFUL_CHANGE"
    snapshots = await client.get(f"/companies/{company_id}/snapshots")
    assert len(snapshots.json()) == 1


@pytest.mark.asyncio
async def test_snapshot_endpoint_captures_baseline_without_body(
    client: httpx.AsyncClient, fake_scraper: FakeScraper
) -> None:
    company_id = await create_company(client)
    fake_scraper.responses = ["<main>Baseline page</main>"]
    response = await client.post(f"/companies/{company_id}/snapshot")
    assert response.status_code == 200
    assert response.json()[0]["normalized_text"] == "Baseline page"


@pytest.mark.asyncio
async def test_unchanged_snapshot_short_circuits(
    client: httpx.AsyncClient, fake_scraper: FakeScraper
) -> None:
    company_id = await create_company(client)
    fake_scraper.responses = [
        "<main>Stable product page</main>",
        "<main>Stable product page</main>",
    ]
    await client.post(f"/companies/{company_id}/scan")
    response = await client.post(f"/companies/{company_id}/scan")
    assert response.json()["results"][0]["result"]["trigger"] == "NO_MEANINGFUL_CHANGE"


@pytest.mark.parametrize(
    ("before", "after"),
    [
        ("Copyright 2025 Acme", "Copyright 2026 Acme"),
        ("Home | About | Contact", "Contact | Home | About"),
    ],
)
@pytest.mark.asyncio
async def test_noise_changes_are_ignored(
    client: httpx.AsyncClient, before: str, after: str
) -> None:
    response = await client.post(
        "/compare", json={"company_name": "Acme", "before": before, "after": after}
    )
    assert response.status_code == 200
    assert response.json()["meaningful_change"] is False


@pytest.mark.parametrize(
    ("after", "trigger"),
    [
        ("We're hiring 20 enterprise account executives across Europe.", "SALES_TEAM_EXPANSION"),
        ("We raised $25M in Series B funding.", "FUNDING"),
        ("Introducing our new workflow automation platform.", "PRODUCT_LAUNCH"),
        ("Our service is now available in Germany and France.", "MARKET_EXPANSION"),
        ("Pricing updated: Pro now starts at $99 per month.", "PRICING_CHANGE"),
        ("Introducing our new enterprise plan.", "ENTERPRISE_EXPANSION"),
    ],
)
@pytest.mark.asyncio
async def test_compare_detects_expected_trigger(
    client: httpx.AsyncClient, after: str, trigger: str
) -> None:
    response = await client.post(
        "/compare",
        json={
            "company_name": "Acme",
            "before": "We help small startups manage sales.",
            "after": after,
        },
    )
    assert response.status_code == 200
    assert response.json()["changes"][0]["trigger"] == trigger


@pytest.mark.asyncio
async def test_ssrf_private_url_is_blocked(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/companies",
        json={"name": "Internal", "website": "http://127.0.0.1:8000", "pages_to_monitor": []},
    )
    assert response.status_code == 422


class BrokenLLM:
    async def classify(self, _: str, __: ChangeCandidate) -> None:
        raise LLMError("malformed response")


@pytest.mark.asyncio
async def test_malformed_llm_output_does_not_crash(client: httpx.AsyncClient) -> None:
    async def broken_classifier() -> TriggerClassifier:
        return TriggerClassifier(BrokenLLM())  # type: ignore[arg-type]

    app.dependency_overrides[get_classifier] = broken_classifier
    response = await client.post(
        "/compare",
        json={"company_name": "Acme", "before": "Old copy", "after": "Different copy"},
    )
    assert response.status_code == 200
    assert response.json()["changes"][0]["trigger"] == "GENERAL_CHANGE"


@pytest.mark.asyncio
async def test_deterministic_fallback_needs_no_api_key(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/compare",
        json={"company_name": "Acme", "before": "Bootstrapped", "after": "We raised $12M funding"},
    )
    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    assert body["changes"][0]["trigger"] == "FUNDING"
