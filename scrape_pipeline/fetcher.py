"""HTTP fetcher: retries with exponential backoff and user-agent rotation."""

import logging
import random
import time

import httpx

from .config import RETRYABLE_STATUS_CODES, USER_AGENTS, RunConfig

log = logging.getLogger("scrape_pipeline")


class FetchError(Exception):
    """Raised when a page cannot be fetched after all attempts."""


class HttpFetcher:
    """httpx client with retry/backoff, UA rotation and an injectable transport."""

    def __init__(
        self, cfg: RunConfig, transport: httpx.BaseTransport | None = None
    ) -> None:
        self._cfg = cfg
        self._client = httpx.Client(
            transport=transport,
            follow_redirects=True,
            timeout=httpx.Timeout(cfg.request_timeout_s),
        )

    def fetch(self, url: str) -> str:
        """Fetch one page and return its HTML text (FetchError on failure)."""
        cfg = self._cfg
        attempts = cfg.retries + 1
        last_error = "unknown"
        for attempt in range(attempts):
            try:
                resp = self._client.get(
                    url, headers={"User-Agent": random.choice(USER_AGENTS)}
                )
            except httpx.TransportError as exc:
                last_error = f"network error: {type(exc).__name__}"
            else:
                if resp.status_code == 200:
                    return resp.text
                if resp.status_code in RETRYABLE_STATUS_CODES:
                    last_error = f"HTTP {resp.status_code}"
                else:
                    raise FetchError(
                        f"{url}: HTTP {resp.status_code} (not retryable)"
                    )
            if attempt < attempts - 1:
                delay = cfg.backoff_s * (2 ** attempt) * random.uniform(0.5, 1.0)
                log.debug(
                    "retry %d for %s in %.1fs (%s)",
                    attempt + 1, url, delay, last_error,
                )
                time.sleep(delay)
        raise FetchError(f"{url}: failed after {attempts} attempts ({last_error})")

    def close(self) -> None:
        """Close the underlying httpx client."""
        self._client.close()
