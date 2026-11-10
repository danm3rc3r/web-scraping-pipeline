"""Command-line interface: argument parsing, validation and entry point."""

import argparse
import json
import logging
import sys
from pathlib import Path
from urllib.parse import urlsplit

from .config import (
    DEFAULT_DELAY_MAX_S,
    DEFAULT_DELAY_MIN_S,
    DEFAULT_GLOBAL_TIMEOUT_S,
    DEFAULT_MAX_BOOKS,
    DEFAULT_MAX_PAGES,
    DEFAULT_RETRIES,
    RunConfig,
)
from .pipeline import run_pipeline

log = logging.getLogger("scrape_pipeline")

_DESCRIPTION = (
    "Scrape book catalogues into JSONL with retries, proxy rotation and "
    "optional headless rendering."
)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser (flags appear as their stages land, D10)."""
    parser = argparse.ArgumentParser(
        prog="scrape_pipeline",
        description=_DESCRIPTION,
    )
    parser.add_argument(
        "--start-url",
        required=True,
        help="Starting catalogue URL; must use http:// or https://.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=DEFAULT_MAX_PAGES,
        help="Maximum number of catalogue pages to follow (default: %(default)s).",
    )
    parser.add_argument(
        "--proxy-file",
        type=Path,
        default=None,
        metavar="PATH",
        help="File with one proxy URL per line.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Render pages with headless Chromium "
             "(requires requirements-headless.txt; falls back to HTTP "
             "when Playwright is unavailable).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data.jsonl"),
        metavar="PATH",
        help="JSONL output file (default: data.jsonl).",
    )
    parser.add_argument(
        "--max-books",
        type=int,
        default=DEFAULT_MAX_BOOKS,
        help="Budget of catalogue entries processed (default: %(default)s).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        nargs=2,
        default=[DEFAULT_DELAY_MIN_S, DEFAULT_DELAY_MAX_S],
        metavar=("MIN_S", "MAX_S"),
        help="Politeness delay range in seconds, MIN then MAX.",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help="Extra retry attempts for transient HTTP errors (default: %(default)s).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_GLOBAL_TIMEOUT_S,
        help="Global run timeout in seconds (default: %(default)s).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    return parser


def build_config(argv: list[str] | None = None) -> RunConfig:
    """Parse arguments and return a validated RunConfig (exit code 2 on errors)."""
    parser = build_parser()
    args = parser.parse_args(argv)
    scheme = urlsplit(args.start_url).scheme.lower()
    if scheme not in ("http", "https"):
        parser.error(f"--start-url must be an http(s):// URL, got: {scheme or 'none'}")
    if args.max_pages < 1:
        parser.error("--max-pages must be >= 1")
    if args.proxy_file is not None and not args.proxy_file.is_file():
        parser.error(f"proxy file not found: {args.proxy_file}")
    if args.max_books < 1:
        parser.error("--max-books must be >= 1")
    if args.delay[0] <= 0 or args.delay[1] <= 0 or args.delay[0] > args.delay[1]:
        parser.error("--delay requires MIN <= MAX and both values > 0")
    if args.retries < 0:
        parser.error("--retries must be >= 0")
    if args.timeout < 1:
        parser.error("--timeout must be >= 1")
    return RunConfig(
        start_url=args.start_url,
        max_pages=args.max_pages,
        max_books=args.max_books,
        out=args.out,
        delay_min_s=args.delay[0],
        delay_max_s=args.delay[1],
        retries=args.retries,
        global_timeout_s=args.timeout,
        proxy_file=args.proxy_file,
        headless=args.headless,
        verbose=args.verbose,
    )


def configure_logging(cfg: RunConfig) -> None:
    """Configure the scrape_pipeline logger (DEBUG with --verbose)."""
    logging.basicConfig(
        level=logging.DEBUG if cfg.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: build the config, run the pipeline, return exit code."""
    cfg = build_config(argv)
    configure_logging(cfg)
    try:
        stats = run_pipeline(cfg)
    except KeyboardInterrupt:
        log.warning("interrupted by user")
        return 130
    except OSError as exc:
        log.error("%s", exc)
        return 2
    print(json.dumps(stats.as_dict()), file=sys.stderr)
    return 0 if (stats.ok > 0 or stats.skipped_dup > 0) else 1
