"""Site-specific parsers for books.toscrape.com (decision D11)."""

import re
from dataclasses import dataclass
from decimal import Decimal
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from .config import RATING_CLASSES

_PRICE_RE = re.compile(r"[\d,]+(?:\.\d+)?")


class ParseError(Exception):
    """Raised when a page is missing required fields."""


@dataclass(frozen=True)
class CatalogEntry:
    """One card from the catalogue listing page."""

    url: str
    title: str
    price: Decimal | None
    rating: int  # 0..5, 0 = not recognised


@dataclass(frozen=True)
class Book:
    """Full record parsed from a book detail page."""

    url: str
    upc: str
    title: str
    price: Decimal
    rating: int
    description: str


def parse_price(text: str) -> Decimal:
    """Extract a Decimal price from a price string (digits, commas, dot)."""
    match = _PRICE_RE.search(text)
    if match is None:
        raise ParseError(f"cannot parse price from: {text!r}")
    return Decimal(match.group(0).replace(",", ""))


def parse_rating(star_el: Tag) -> int:
    """Map the last star-rating class word (One..Five) to 1..5, else 0."""
    classes = star_el.get("class") or []
    if not classes:
        return 0
    return RATING_CLASSES.get(classes[-1], 0)


def parse_catalog_page(html: str, page_url: str) -> list[CatalogEntry]:
    """Parse all book cards from a catalogue page (urls made absolute)."""
    soup = BeautifulSoup(html, "lxml")
    entries: list[CatalogEntry] = []
    for pod in soup.select("article.product_pod"):
        link = pod.select_one("h3 a")
        title = ""
        href = ""
        if link is not None:
            title = link.get("title") or link.get_text(strip=True)
            href = link.get("href", "")
        price_el = pod.select_one("p.price_color")
        price: Decimal | None = None
        if price_el is not None:
            price = parse_price(price_el.get_text(strip=True))
        star_el = pod.select_one("p.star-rating")
        rating = parse_rating(star_el) if star_el is not None else 0
        entries.append(
            CatalogEntry(
                url=urljoin(page_url, href),
                title=title,
                price=price,
                rating=rating,
            )
        )
    return entries


def parse_next_link(html: str, page_url: str) -> str | None:
    """Resolve the li.next link to an absolute URL (None when absent)."""
    soup = BeautifulSoup(html, "lxml")
    link = soup.select_one("li.next a")
    if link is None:
        return None
    return urljoin(page_url, link.get("href", ""))


def parse_book_detail(html: str, entry: CatalogEntry) -> Book:
    """Parse a book detail page into a Book (ParseError on missing fields)."""
    soup = BeautifulSoup(html, "lxml")
    title_el = soup.select_one("h1")
    title = title_el.get_text(strip=True) if title_el is not None else ""
    price_el = soup.select_one("p.price_color")
    price: Decimal | None = None
    if price_el is not None:
        price = parse_price(price_el.get_text(strip=True))
    star_el = soup.select_one("p.star-rating")
    rating = parse_rating(star_el) if star_el is not None else 0
    desc_div = soup.select_one("div#product_description")
    desc_p = desc_div.find_next("p") if desc_div is not None else None
    description = desc_p.get_text(" ", strip=True) if desc_p is not None else ""
    upc = ""
    table = soup.select_one("table.table-striped")
    if table is not None:
        for th in table.find_all("th"):
            if th.get_text(strip=True).upper().startswith("UPC"):
                td = th.find_next("td")
                upc = td.get_text(strip=True) if td is not None else ""
                break
    missing = [
        name
        for name, value in (
            ("title", title),
            ("price", price),
            ("description", description),
        )
        if not value
    ]
    if missing:
        raise ParseError(f"missing fields: {', '.join(sorted(missing))}")
    return Book(
        url=entry.url,
        upc=upc,
        title=title,
        price=price,
        rating=rating,
        description=description,
    )
