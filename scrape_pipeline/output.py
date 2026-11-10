"""JSONL output: book record writer and seen-URL store (design 04a, sections 3.3, 3.4, 4.7)."""

import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from .parser import Book

log = logging.getLogger("scrape_pipeline")


class JsonlWriter:
    """Append book records to a JSONL file, one record per line."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self._path.open("a", encoding="utf-8")

    def write_book(self, book: Book) -> None:
        record = {
            "url": book.url,
            "upc": book.upc,
            "title": book.title,
            "price": float(book.price),
            "rating": book.rating,
            "description": book.description,
            "fetched_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        self._file.write(json.dumps(record, ensure_ascii=False) + "\n")

    def close(self) -> None:
        self._file.close()


class SeenStore:
    """Track already-written book URLs in an append-only sidecar file."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._seen: set[str] = set()
        if path.is_file():
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    url = str(json.loads(line)["url"])
                except (ValueError, KeyError, TypeError):
                    log.warning("corrupt line in seen file, skipped")
                    continue
                self._seen.add(url)

    def contains(self, url: str) -> bool:
        return url in self._seen

    def add(self, url: str) -> None:
        self._seen.add(url)
        sha = hashlib.sha256(url.encode("utf-8")).hexdigest()
        line = json.dumps({"sha256": sha, "url": url})
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def close(self) -> None:
        pass
