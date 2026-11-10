"""Catalog pipeline (stage S2): walk pages and collect per-book stats."""

import logging
import random
import time

from .config import RunConfig, RunStats
from .fetcher import FetchError, HttpFetcher
from .headless import HeadlessFetcher, HeadlessUnavailable
from .parser import parse_catalog_page, parse_next_link

log = logging.getLogger("scrape_pipeline")


def _make_source(cfg: RunConfig) -> HttpFetcher | HeadlessFetcher:
    """Choose the page source: headless when enabled, HTTP fallback (D5)."""
    if not cfg.headless:
        return HttpFetcher(cfg)
    try:
        return HeadlessFetcher()
    except HeadlessUnavailable as exc:
        log.warning("headless unavailable (%s); falling back to HTTP", exc)
        return HttpFetcher(cfg)


def run_pipeline(cfg: RunConfig) -> RunStats:
    """Walk the catalogue for up to cfg.max_pages pages and return run stats.

    Stage S2 semantics: ok counts processed catalogue cards; detail pages
    and JSONL output are added in stage S5 (design section 8, S2).
    """
    start = time.monotonic()
    stats = RunStats()
    source = _make_source(cfg)
    try:
        next_url: str | None = cfg.start_url
        for page_no in range(1, cfg.max_pages + 1):
            if next_url is None:
                break
            if time.monotonic() - start >= cfg.global_timeout_s:
                log.warning("global timeout reached, stopping")
                break
            if page_no > 1:
                time.sleep(random.uniform(cfg.delay_min_s, cfg.delay_max_s))
            try:
                html = source.fetch(next_url)
            except FetchError as exc:
                log.warning("catalog page %d failed: %s", page_no, exc)
                stats.failed += 1
                break
            entries = parse_catalog_page(html, next_url)
            if not entries and page_no == 1:
                log.error("no entries found on first page; aborting")
                break
            for entry in entries:
                stats.ok += 1
                log.info("title: %s", entry.title)
            next_url = parse_next_link(html, next_url)
    finally:
        source.close()
        stats.elapsed_s = time.monotonic() - start
    return stats
