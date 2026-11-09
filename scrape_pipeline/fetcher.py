"""HTTP fetcher: retries with backoff, user-agent rotation and proxy rotation."""

import logging
import random
import time
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import httpx

from .config import RETRYABLE_STATUS_CODES, USER_AGENTS, RunConfig

log = logging.getLogger("scrape_pipeline")


class FetchError(Exception):
    """Raised when a page cannot be fetched after all attempts."""

PROXY_SCHEMES = ("http", "https", "socks5", "socks5h")


def mask_proxy_url(url: str) -> str:
    """Mask proxy credentials for logging: ``http://user:pass@host:8080`` becomes
    ``http://user:***@host:8080``. URLs without a password are unchanged."""
    parts = urlsplit(url)
    if parts.password is None:
        return url
    hostport = parts.netloc.rpartition("@")[-1]
    netloc = f"{parts.username or ''}:***@{hostport}"
    return urlunsplit(
        (parts.scheme, netloc, parts.path, parts.query, parts.fragment)
    )


def parse_proxy_file(path: Path) -> list[str]:
    """Read proxy URLs from a file, one per line.

    Blank lines and ``#`` comments are skipped. A line whose scheme is not
    http/https/socks5/socks5h, that has no netloc or a non-numeric port, is
    logged masked and
    skipped. An empty result means the run goes direct.
    """
    proxies = []
    for line in path.read_text(encoding="utf-8").splitlines():
        candidate = line.strip()
        if not candidate or candidate.startswith("#"):
            continue
        parts = urlsplit(candidate)
        if parts.scheme not in PROXY_SCHEMES or not parts.netloc:
            log.warning("invalid proxy line skipped: %s", mask_proxy_url(candidate))
            continue
        try:
            _ = parts.port
        except ValueError:
            log.warning("invalid proxy line skipped: %s", mask_proxy_url(candidate))
            continue
        proxies.append(candidate)
    return proxies


class _ProxyRoundRobinTransport(httpx.BaseTransport):
    """Round-robin across one HTTPTransport per proxy (httpx docs pattern)."""

    def __init__(self, proxies: list[str], **kwargs) -> None:
        self._transports = [httpx.HTTPTransport(proxy=p, **kwargs) for p in proxies]
        self._index = 0

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        transport = self._transports[self._index]
        self._index = (self._index + 1) % len(self._transports)
        return transport.handle_request(request)

    def close(self) -> None:
        for transport in self._transports:
            transport.close()



class HttpFetcher:
    """httpx client: retry/backoff, UA rotation and proxy rotation.

    An injectable transport (test seam) overrides the proxy transport.
    """

    def __init__(
        self, cfg: RunConfig, transport: httpx.BaseTransport | None = None
    ) -> None:
        self._cfg = cfg
        if transport is None and cfg.proxy_file is not None:
            proxies = parse_proxy_file(cfg.proxy_file)
            if proxies:
                transport = _ProxyRoundRobinTransport(proxies)
                log.info("proxy rotation: %d proxies loaded", len(proxies))
            else:
                log.warning("no valid proxies in %s, running direct", cfg.proxy_file)
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
