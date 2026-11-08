"""Runtime configuration and shared constants for the scraper."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RunConfig:
    """All runtime options for one scraper run (CLI-only, no env file)."""

    start_url: str
    max_pages: int = 3
    max_books: int = 25
    out: Path = Path("data.jsonl")
    delay_min_s: float = 1.0
    delay_max_s: float = 3.0
    retries: int = 3
    backoff_s: float = 2.0
    request_timeout_s: float = 15.0
    global_timeout_s: float = 300.0
    headless: bool = False
    proxy_file: Path | None = None
    verbose: bool = False


DEFAULT_MAX_PAGES = 3
DEFAULT_MAX_BOOKS = 25
DEFAULT_DELAY_MIN_S = 1.0
DEFAULT_DELAY_MAX_S = 3.0
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF_S = 2.0
DEFAULT_REQUEST_TIMEOUT_S = 15.0
DEFAULT_GLOBAL_TIMEOUT_S = 300.0
DEFAULT_HEADLESS_TIMEOUT_MS = 30_000
HEADLESS_RETRY_WAIT_S = 5.0

RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})

RATING_CLASSES = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}

USER_AGENTS: tuple[str, ...] = (
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
    ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 "
    "Firefox/127.0"),
    ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15"),
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0"),
)


@dataclass
class RunStats:
    """Counters collected during one run, printed as a single JSON line."""

    ok: int = 0
    failed: int = 0
    skipped_dup: int = 0
    elapsed_s: float = 0.0

    def as_dict(self) -> dict:
        """Return the stats as a JSON-serializable dict (elapsed_s rounded to 0.01)."""
        return {
            "ok": self.ok,
            "failed": self.failed,
            "skipped_dup": self.skipped_dup,
            "elapsed_s": round(self.elapsed_s, 2),
        }
