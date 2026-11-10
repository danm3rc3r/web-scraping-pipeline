"""Catalog pipeline (stage S2): walk pages and collect per-book stats."""

import logging
import random
import time

from .config import RunConfig, RunStats
from .fetcher import FetchError, HttpFetcher
from .headless import HeadlessFetcher, HeadlessUnavailable
from .output import JsonlWriter, SeenStore
from .parser import ParseError, parse_book_detail, parse_catalog_page, parse_next_link

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
    """Walk the catalogue, fetch book details and write deduplicated JSONL."""
    start = time.monotonic()
    stats = RunStats()
    source = _make_source(cfg)
    writer = JsonlWriter(cfg.out)
    seen = SeenStore(cfg.out.with_name(cfg.out.stem + ".seen.jsonl"))
    try:
        budget = cfg.max_books
        next_url: str | None = cfg.start_url
        for page_no in range(1, cfg.max_pages + 1):
            if budget <= 0 or next_url is None:
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
            if not entries:
                if page_no == 1:
                    log.error("no entries found on first page; aborting")
                    break
                log.warning("page %d: no entries found", page_no)
            for entry in entries:
                if budget <= 0:
                    break
                if seen.contains(entry.url):
                    stats.skipped_dup += 1
                    log.info("skip (duplicate): %s", entry.title)
                    budget -= 1
                    continue
                time.sleep(random.uniform(cfg.delay_min_s, cfg.delay_max_s))
                if time.monotonic() - start >= cfg.global_timeout_s:
                    log.warning("global timeout reached, stopping")
                    break
                try:
                    detail = source.fetch(entry.url)
                except FetchError as exc:
                    stats.failed += 1
                    log.warning("detail fetch failed: %s", exc)
                    budget -= 1
                    continue
                try:
                    book = parse_book_detail(detail, entry)
                except ParseError as exc:
                    stats.failed += 1
                    log.warning("parse failed for %s: %s", entry.url, exc)
                    budget -= 1
                    continue
                writer.write_book(book)
                seen.add(entry.url)
                stats.ok += 1
                log.info("saved: %s (%s)", book.title, book.url)
                budget -= 1
            next_url = parse_next_link(html, next_url)
    finally:
        source.close()
        writer.close()
        seen.close()
        stats.elapsed_s = time.monotonic() - start
    return stats
