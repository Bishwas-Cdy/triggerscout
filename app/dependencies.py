from functools import lru_cache

from app.config import get_settings
from app.services.classifier import TriggerClassifier
from app.services.llm import LLMClient
from app.services.scraper import Scraper


@lru_cache
def _cached_scraper() -> Scraper:
    return Scraper(get_settings())


@lru_cache
def _cached_classifier() -> TriggerClassifier:
    return TriggerClassifier(LLMClient(get_settings()))


async def get_scraper() -> Scraper:
    return _cached_scraper()


async def get_classifier() -> TriggerClassifier:
    return _cached_classifier()
