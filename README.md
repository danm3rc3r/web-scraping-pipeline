# web-scraping-pipeline

## What it is

A small web scraping CLI that shows the mechanics professional scraping jobs are
paid for: retries with exponential backoff, round-robin proxy rotation,
User-Agent rotation, politeness delays and optional headless rendering. Results
go to an append-only JSONL file with cross-run dedupe and per-run statistics.
The demo target is books.toscrape.com, a public scraping sandbox.

## Features

- Exponential backoff with jitter on 429/5xx and network errors
- Round-robin proxy rotation from a file (passwords masked in logs)
- Random User-Agent per request
- Politeness delay between requests (configurable)
- Optional headless rendering via Playwright with graceful fallback to plain HTTP
- Append-only JSONL with URL-hash dedupe across runs
- Per-run stats (ok/failed/skipped/elapsed) printed to stderr
- Global timeout for a graceful stop
- Docker image (ships without Playwright — `--headless` falls back to plain HTTP)

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
| `--max-pages` | 3 | catalogue pages to follow |
| `--verbose` | off | debug logging |
| `--proxy-file` | — | file with one proxy URL per line |
| `--headless` | off | render pages with Playwright (optional extra) |
| `--out` | `data.jsonl` | JSONL output file (append mode) |
| `--max-books` | 25 | budget of catalogue entries processed |
| `--delay` | `1.0 3.0` | politeness delay range in seconds, MIN then MAX |
| `--retries` | 3 | extra retry attempts for transient HTTP errors |
| `--timeout` | 300.0 | global run timeout in seconds |

Examples:

```
# proxy rotation
python -m scrape_pipeline --start-url https://books.toscrape.com/ --proxy-file proxies.txt

# headless rendering (optional; one-time browser install)
pip install -r requirements-headless.txt
python -m playwright install chromium
python -m scrape_pipeline --start-url https://books.toscrape.com/ --headless

# re-run — duplicates are skipped, the file is not re-written
python -m scrape_pipeline --start-url https://books.toscrape.com/ --max-pages 1 --out data.jsonl
```

### Docker

```
docker build -t web-scraping-pipeline .
docker run --rm -v ./data:/out web-scraping-pipeline --start-url https://books.toscrape.com/ --out /out/data.jsonl
```

The Docker image ships without Playwright: `--headless` falls back to plain HTTP.

### Output format

One JSON object per line:

```
{"url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html", "upc": "a897fe39b1053632", "title": "A Light in the Attic", "price": 51.77, "rating": 3, "description": "It's hard to imagine a world without A Light in the Attic. This now-classic collection of poetry and drawings from Shel Silverstein celebrates its 20th anniversary with this special edition. Silverstein's humorous and creative verse can amuse the dowdiest of readers. Lemon-faced adults and fidgety kids sit still and read these rhythmic words and laugh and smile and love th It's hard to imagine a world without A Light in the Attic. This now-classic collection of poetry and drawings from Shel Silverstein celebrates its 20th anniversary with this special edition. Silverstein's humorous and creative verse can amuse the dowdiest of readers. Lemon-faced adults and fidgety kids sit still and read these rhythmic words and laugh and smile and love that Silverstein. Need proof of his genius? RockabyeRockabye baby, in the treetopDon't you know a treetopIs no safe place to rock?And who put you up there,And your cradle, too?Baby, I think someone down here'sGot it in for you. Shel, you never sounded so good. ...more", "fetched_at": "2026-11-11T06:21:43Z"}
{"url": "https://books.toscrape.com/catalogue/tipping-the-velvet_999/index.html", "upc": "90fa61229261140a", "title": "Tipping the Velvet", "price": 53.74, "rating": 1, "description": "\"Erotic and absorbing...Written with starling power.\"--\"The New York Times Book Review \" Nan King, an oyster girl, is captivated by the music hall phenomenon Kitty Butler, a male impersonator extraordinaire treading the boards in Canterbury. Through a friend at the box office, Nan manages to visit all her shows and finally meet her heroine. Soon after, she becomes Kitty's \"Erotic and absorbing...Written with starling power.\"--\"The New York Times Book Review \" Nan King, an oyster girl, is captivated by the music hall phenomenon Kitty Butler, a male impersonator extraordinaire treading the boards in Canterbury. Through a friend at the box office, Nan manages to visit all her shows and finally meet her heroine. Soon after, she becomes Kitty's dresser and the two head for the bright lights of Leicester Square where they begin a glittering career as music-hall stars in an all-singing and dancing double act. At the same time, behind closed doors, they admit their attraction to each other and their affair begins. ...more", "fetched_at": "2026-11-11T06:21:44Z"}
```

| Field | Type | Note |
|---|---|---|
| `url` | string | absolute book detail URL |
| `upc` | string | from the detail page table |
| `title` | string | full title from the detail page |
| `price` | float | e.g. 51.77 |
| `rating` | int | 0–5 |
| `description` | string | from the detail page |
| `fetched_at` | string | UTC, `%Y-%m-%dT%H:%M:%SZ` |

## Configuration

No config file and no environment variables: everything is a CLI flag.

Proxy file format: one proxy per line, `scheme://user:password@host:port`.
Supported schemes: `http`, `https`, `socks5`. Blank lines and lines starting
with `#` are ignored. Example: `sample_data/proxies.example.txt`.

## Limitations

1. The parser targets the books.toscrape.com page structure; other sites need
   other selectors (the pipeline itself is site-agnostic).
2. Requests are sequential by design (no parallel workers).
3. Dedupe is by URL only.
4. Headless mode needs a one-time `playwright install chromium` (~150 MB).
5. No persistence beyond the JSONL output and the seen file.
6. Not for aggressive scraping — the built-in politeness delays are a feature.

## License

MIT — see [LICENSE](LICENSE).
