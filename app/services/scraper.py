import asyncio
import logging
from urllib.parse import urljoin

import httpx

from app.config import Settings
from app.services.url_safety import UnsafeURLError, assert_public_url

logger = logging.getLogger(__name__)


class ScrapeError(RuntimeError):
    pass


class PageTooLargeError(ScrapeError):
    pass


class Scraper:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def fetch(self, url: str) -> str:
        current_url = await assert_public_url(url)
        timeout = httpx.Timeout(self._settings.request_timeout_seconds)
        headers = {"User-Agent": self._settings.user_agent, "Accept": "text/html,*/*;q=0.8"}
        async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
            for redirect_count in range(4):
                response = await self._request_with_retries(client, current_url)
                try:
                    if response.is_redirect:
                        if redirect_count == 3:
                            raise ScrapeError("Too many redirects")
                        location = response.headers.get("location")
                        if not location:
                            raise ScrapeError("Redirect response did not include a location")
                        current_url = await assert_public_url(urljoin(current_url, location))
                        continue
                    if response.is_error:
                        raise ScrapeError(f"Upstream returned {response.status_code}")
                    content_type = response.headers.get("content-type", "")
                    if content_type and not any(
                        allowed in content_type
                        for allowed in ("text/html", "text/plain", "application/xhtml")
                    ):
                        raise ScrapeError(f"Unsupported content type: {content_type}")
                    declared_size = response.headers.get("content-length")
                    if declared_size:
                        try:
                            if int(declared_size) > self._settings.max_response_bytes:
                                raise PageTooLargeError("Response exceeds configured size limit")
                        except ValueError:
                            logger.info(
                                "Ignoring invalid Content-Length", extra={"url": current_url}
                            )
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > self._settings.max_response_bytes:
                            raise PageTooLargeError("Response exceeds configured size limit")
                    return bytes(body).decode(response.encoding or "utf-8", errors="replace")
                finally:
                    await response.aclose()
        raise ScrapeError("Unable to fetch page")

    async def _request_with_retries(self, client: httpx.AsyncClient, url: str) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(self._settings.http_retries + 1):
            try:
                request = client.build_request("GET", url)
                response = await client.send(request, stream=True, follow_redirects=False)
                if response.status_code < 500:
                    return response
                await response.aclose()
                last_error = ScrapeError(f"Upstream returned {response.status_code}")
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = exc
            if attempt < self._settings.http_retries:
                await asyncio.sleep(0.15 * (2**attempt))
        logger.warning("Page fetch failed", extra={"url": url})
        raise ScrapeError("Page fetch failed after retries") from last_error


__all__ = ["PageTooLargeError", "ScrapeError", "Scraper", "UnsafeURLError"]
