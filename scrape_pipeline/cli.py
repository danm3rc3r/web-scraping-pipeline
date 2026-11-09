"""Command-line interface: argument parsing, validation and entry point."""

import argparse
import json
import logging
import sys
from pathlib import Path
from urllib.parse import urlsplit

from .config import DEFAULT_MAX_PAGES, RunConfig
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
    return RunConfig(
        start_url=args.start_url,
        max_pages=args.max_pages,
        proxy_file=args.proxy_file,
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
