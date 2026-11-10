"""Playwright (Chromium, headless) page source. Optional dependency (D4)."""

import contextlib
import logging
import time

from .config import DEFAULT_HEADLESS_TIMEOUT_MS, HEADLESS_RETRY_WAIT_S
from .fetcher import FetchError

log = logging.getLogger("scrape_pipeline")


class HeadlessUnavailable(RuntimeError):
    """Playwright is not installed or the Chromium browser cannot be launched."""


class HeadlessFetcher:
    """Playwright (Chromium, headless) page source. Optional dependency (D4).

    The dependency is imported lazily so the core package stays usable without
    Playwright installed; an import or launch failure surfaces as
    HeadlessUnavailable, which the pipeline maps to the HTTP fallback (D5).
    """

    def __init__(self, timeout_ms: int = DEFAULT_HEADLESS_TIMEOUT_MS) -> None:
        self._timeout_ms = timeout_ms
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise HeadlessUnavailable("playwright is not installed")
        self._pw = None
        try:
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(headless=True)
            self._page = self._browser.new_page()
        except Exception as exc:  # noqa: BLE001 - any launch failure -> HeadlessUnavailable (D5)
            if self._pw is not None:
                with contextlib.suppress(Exception):
                    self._pw.stop()
            raise HeadlessUnavailable(f"cannot launch chromium: {exc}")

    def fetch(self, url: str) -> str:
        """Load the page and return its rendered HTML (two attempts total)."""
        for attempt in (1, 2):
            try:
                self._page.goto(
                    url, timeout=self._timeout_ms, wait_until="domcontentloaded"
                )
                return self._page.content()
            except Exception:  # noqa: BLE001 - retry on any goto error (design: 2 attempts)
                if attempt == 1:
                    time.sleep(HEADLESS_RETRY_WAIT_S)
        raise FetchError(f"{url}: headless fetch failed after 2 attempts")

    def close(self) -> None:
        """Close the browser and stop the Playwright driver."""
        try:
            self._browser.close()
        finally:
            self._pw.stop()
