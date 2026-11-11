"""Offline smoke test (AC-2): parser, output and proxy contracts on local fixtures.

Run from the repository root:  python smoke/run_smoke.py
Prints SMOKE OK and exits 0 on success.
"""

import json
import sys
import tempfile
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scrape_pipeline.fetcher import mask_proxy_url
from scrape_pipeline.output import JsonlWriter, SeenStore
from scrape_pipeline.parser import (
    Book,
    CatalogEntry,
    parse_book_detail,
    parse_catalog_page,
    parse_next_link,
    parse_price,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CATALOG_URL = "https://books.toscrape.com/"
NEXT_URL = "https://books.toscrape.com/catalogue/page-2.html"
DETAIL_URL = "https://books.toscrape.com/catalogue/fixture-detail_3000/index.html"


def check_catalog() -> None:
    html = (FIXTURES / "catalog.html").read_text(encoding="utf-8")
    entries = parse_catalog_page(html, CATALOG_URL)
    assert len(entries) == 2, entries
    one, two = entries
    assert one.url == "https://books.toscrape.com/catalogue/fixture-one_1000/index.html", one
    assert one.title == "Fixture Book One", one
    assert one.price == Decimal("9.99"), one
    assert one.rating == 4, one
    assert two.url == "https://books.toscrape.com/catalogue/fixture-two_2000/index.html", two
    assert two.title == "Fixture Book Two", two
    assert two.price == Decimal("51.77"), two
    assert two.rating == 3, two
    assert parse_next_link(html, CATALOG_URL) == NEXT_URL


def check_detail() -> None:
    entry = CatalogEntry(url=DETAIL_URL, title="Fixture Detail Book",
                         price=Decimal("9.99"), rating=4)
    html = (FIXTURES / "detail.html").read_text(encoding="utf-8")
    book = parse_book_detail(html, entry)
    assert book.upc == "fixture-0001", book
    assert book.title == "Fixture Detail Book", book
    assert book.price == Decimal("9.99"), book
    assert book.rating == 4, book
    assert book.description == "A fictitious description for the smoke fixture.", book


def check_price_vectors() -> None:
    assert parse_price("\u00a351.77") == Decimal("51.77")
    assert parse_price("\u00a31,000.00") == Decimal("1000.00")


def check_proxy_masking() -> None:
    masked = mask_proxy_url("http://user-01:secret-01@proxy-a.example.com:8080")
    assert masked == "http://user-01:***@proxy-a.example.com:8080", masked
    plain = mask_proxy_url("http://proxy-a.example.com:8080")
    assert plain == "http://proxy-a.example.com:8080", plain


def check_seen_store() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "seen.jsonl"
        path.write_text(
            '{"sha256": "x", "url": "https://books.toscrape.com/catalogue/a/index.html"}\n'
            "not-json-line\n",
            encoding="utf-8",
        )
        store = SeenStore(path)
        assert store.contains("https://books.toscrape.com/catalogue/a/index.html")
        assert not store.contains("https://books.toscrape.com/catalogue/b/index.html")
        store.add("https://books.toscrape.com/catalogue/b/index.html")
        assert store.contains("https://books.toscrape.com/catalogue/b/index.html")
        store.close()


def check_record_shape() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "sub" / "data.jsonl"
        writer = JsonlWriter(out)
        writer.write_book(Book(
            url=DETAIL_URL,
            upc="fixture-0001",
            title="Fixture Detail Book",
            price=Decimal("9.99"),
            rating=4,
            description="A fictitious description for the smoke fixture.",
        ))
        writer.close()
        lines = out.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1, lines
        keys = tuple(json.loads(lines[0]).keys())
        assert keys == ("url", "upc", "title", "price", "rating", "description",
                        "fetched_at"), keys


def main() -> int:
    check_catalog()
    check_detail()
    check_price_vectors()
    check_proxy_masking()
    check_seen_store()
    check_record_shape()
    print("SMOKE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
