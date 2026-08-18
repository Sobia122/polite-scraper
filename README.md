# Polite Scraper API (BE-05)

A polite, resilient web scraper built with Python, BeautifulSoup, and Pydantic. It collects 60 book records across 3 catalogue pages from Books to Scrape, validates each record against a strict schema, and generates execution reports without crashing on failures.

## Target Classification
- **Target Site**: Books to Scrape (`https://books.toscrape.com`)
- **Scope**: First 3 catalogue pages (60 unique books)
- **Robots.txt Status**: No `robots.txt` found.
- **Permission**: The site is a public sandbox created specifically for scraping practice.
- **Statement**: *I will not reuse this code on another site without checking its rules and terms first.*

## Politeness & Robustness Features
- **Custom User-Agent**: Identifies the bot politely with repo details.
- **Rate Limiting**: 500ms delay between live network requests.
- **HTML Caching**: Caches pages locally in `cache/` to prevent network spamming during development.
- **Schema Validation**: Uses Pydantic to ensure price floats, valid URLs, and required fields.
- **Idempotency**: Rerunning produces the exact same 60 records without duplication.

## Setup & Execution

1. **Set up virtual environment & install dependencies:**
   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   pip install requests beautifulsoup4 pydantic pytest
