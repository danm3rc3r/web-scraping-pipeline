# web-scraping-pipeline

## What it is

A small web scraping CLI that covers the mechanics of production scraping:
retries with exponential backoff, round-robin proxy rotation, User-Agent
rotation, politeness delays and optional headless rendering. Results go to an
append-only JSONL file, deduplicated across runs, with per-run statistics.
The demo target is books.toscrape.com, a public site built for scraping
practice.

## Features

- Exponential backoff with jitter on 429/5xx and network errors
- Round-robin proxy rotation from a file (passwords masked in logs)
- Random User-Agent per request
- Politeness delay between requests (configurable)
- Optional headless rendering via Playwright, with fallback to plain HTTP
- Append-only JSONL, deduplicated by URL hash across runs
- Per-run stats (ok/failed/skipped/elapsed) printed to stderr
- Global timeout that stops the run cleanly
- Docker image, shipped without Playwright (`--headless` falls back to plain HTTP)

## Quickstart (5 minutes)

```
git clone https://github.com/danm3rc3r/web-scraping-pipeline.git
cd web-scraping-pipeline

python -m venv .venv
# Windows:  .venv\Scripts\activate      macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt

python -m scrape_pipeline --start-url https://books.toscrape.com/ --max-pages 1 --max-books 10 --out data.jsonl
```

A sample of the output is in `sample_data/sample_output.jsonl`.

## Usage

```
python -m scrape_pipeline --start-url URL [--max-pages N] [--verbose]
                           [--proxy-file PATH] [--headless]
                           [--out PATH] [--max-books N] [--delay MIN MAX]
                           [--retries N] [--timeout SECS]
```

| Flag | Default | Description |
|---|---|---|
| `--start-url` | required | Starting catalogue URL (http/https) |
| `--max-pages` | 3 | Catalogue pages to follow |
| `--verbose` | off | Debug logging |
| `--proxy-file` | (none) | File with one proxy URL per line |
| `--headless` | off | Render pages with Playwright (optional extra) |
| `--out` | `data.jsonl` | JSONL output file (append mode) |
| `--max-books` | 25 | Budget of catalogue entries to process |
| `--delay` | `1.0 3.0` | Politeness delay range in seconds, MIN then MAX |
| `--retries` | 3 | Extra retry attempts for transient HTTP errors |
| `--timeout` | `300.0` | Global run timeout in seconds |

Examples:

```
# proxy rotation
python -m scrape_pipeline --start-url https://books.toscrape.com/ --proxy-file proxies.txt

# headless rendering (optional; one-time browser install)
pip install -r requirements-headless.txt
python -m playwright install chromium
python -m scrape_pipeline --start-url https://books.toscrape.com/ --headless

# re-run: duplicates are skipped, the file is not re-written
python -m scrape_pipeline --start-url https://books.toscrape.com/ --max-pages 1 --out data.jsonl
```

### Docker

```
docker build -t web-scraping-pipeline .
docker run --rm -v ./data:/out web-scraping-pipeline --start-url https://books.toscrape.com/ --out /out/data.jsonl
```

The Docker image ships without Playwright: `--headless` falls back to plain HTTP.

### Output format

One JSON object per line (descriptions are shortened here; the full records
are in `sample_data/sample_output.jsonl`):

```
{"url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html", "upc": "a897fe39b1053632", "title": "A Light in the Attic", "price": 51.77, "rating": 3, "description": "It's hard to imagine a world without A Light in the Attic. This now-classic collection of poetry and drawings from Shel Silverstein ...", "fetched_at": "2026-11-11T06:21:43Z"}
{"url": "https://books.toscrape.com/catalogue/tipping-the-velvet_999/index.html", "upc": "90fa61229261140a", "title": "Tipping the Velvet", "price": 53.74, "rating": 1, "description": "\"Erotic and absorbing...Written with starling power.\"--\"The New York Times Book Review\" Nan King, an oyster girl, is captivated by the music hall phenomenon Kitty Butler ...", "fetched_at": "2026-11-11T06:21:44Z"}
```

| Field | Type | Note |
|---|---|---|
| `url` | string | Absolute book detail URL |
| `upc` | string | From the detail page table |
| `title` | string | Full title from the detail page |
| `price` | float | Example: 51.77 |
| `rating` | int | 1-5 |
| `description` | string | From the detail page |
| `fetched_at` | string | UTC, `%Y-%m-%dT%H:%M:%SZ` |

## Configuration

Everything is a CLI flag: no config file, no environment variables.

Proxy file format: one proxy per line, `scheme://user:password@host:port`.
Supported schemes: `http`, `https`, `socks5`, `socks5h`. Blank lines and
lines starting with `#` are ignored. Example:
`sample_data/proxies.example.txt`.

## Limitations

1. The parser targets the books.toscrape.com page structure. Other sites
   need their own selectors.
2. Requests are sequential by design (no parallel workers).
3. Deduplication is by URL only.
4. Headless mode needs a one-time `playwright install chromium` (a download
   of about 150-175 MB).
5. There is no persistence beyond the JSONL output and the seen file.
6. This tool is not for aggressive scraping. The politeness delays are
   intentional.

## License

MIT. See [LICENSE](LICENSE).