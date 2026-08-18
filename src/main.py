import os
import re
import time
import json
import logging
from datetime import datetime, timezone
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, HttpUrl, Field, ValidationError

# Setup Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Configs & Constants
BASE_URL = "https://books.toscrape.com/catalogue/page-1.html"
HEADERS = {
    "User-Agent": "FlyRankInternship-A9/1.0 (+https://github.com/Sobia122/polite-scraper)"
}
CACHE_DIR = "cache"
OUTPUT_DIR = "output"
TIMEOUT = 10  # Seconds

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

RATING_MAP = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}

# --- STAGE 4: Pydantic Schema ---
class BookSchema(BaseModel):
    title: str = Field(..., min_length=1)
    product_url: HttpUrl
    price_text: str
    price_gbp: float = Field(..., ge=0.0)
    availability_text: str
    rating_text: str
    rating_num: int = Field(..., ge=1, le=5)
    description: str | None = None
    source_page: HttpUrl
    fetched_at: str

# --- STAGE 1: Polite Fetcher with Caching ---
def fetch_with_cache(url: str, filename: str) -> tuple[str, bool]:
    cache_path = os.path.join(CACHE_DIR, filename)
    
    if os.path.exists(cache_path):
        logging.info(f"CACHE HIT: {filename}")
        with open(cache_path, "r", encoding="utf-8") as f:
            return f.read(), True

    logging.info(f"FETCHING: {url}")
    time.sleep(0.5)  # Politeness Delay (500ms)
    
    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    if response.status_code != 200:
        raise ValueError(f"HTTP Error {response.status_code} for URL: {url}")

    html_content = response.text
    with open(cache_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    return html_content, False

def parse_price(price_str: str) -> float:
    match = re.search(r"[\d\.]+", price_str)
    return float(match.group()) if match else 0.0

# --- STAGE 2: Catalogue Discovery ---
def discover_books(max_pages: int = 3) -> tuple[list[tuple[str, str]], int]:
    book_entries = []  # (book_url, source_page_url)
    current_url = BASE_URL
    cache_hits = 0

    for page in range(1, max_pages + 1):
        if not current_url:
            break
            
        page_filename = f"catalogue-page-{page}.html"
        try:
            html, is_cached = fetch_with_cache(current_url, page_filename)
            if is_cached:
                cache_hits += 1
        except Exception as e:
            logging.error(f"Failed catalogue fetch page {page}: {e}")
            break

        soup = BeautifulSoup(html, "html.parser")
        
        # Extract Book Links
        articles = soup.select("article.product_pod")
        for article in articles:
            rel_link = article.h3.a["href"]
            abs_link = urljoin(current_url, rel_link)
            book_entries.append((abs_link, current_url))

        # Find "next" link
        next_btn = soup.select_one("li.next a")
        current_url = urljoin(current_url, next_btn["href"]) if next_btn else None

    # Deduplicate keeping order
    unique_entries = list(dict.fromkeys(book_entries))
    return unique_entries, cache_hits

# --- STAGE 3 & 5: Book Details Extraction & Resilience ---
def extract_book_details(book_url: str, source_page: str, index: int) -> tuple[dict | None, bool]:
    filename = f"book-detail-{index}.html"
    try:
        html, is_cached = fetch_with_cache(book_url, filename)
    except Exception as e:
        logging.error(f"Failed to fetch detail page {book_url}: {e}")
        return None, False

    soup = BeautifulSoup(html, "html.parser")
    main_box = soup.select_one("div.product_main")
    if not main_box:
        return None, is_cached

    title = main_box.h1.text.strip()
    price_text = main_box.select_one("p.price_color").text.strip()
    availability_text = main_box.select_one("p.instock.availability").text.strip()
    
    # Rating Class Parse
    rating_elem = main_box.select_one("p.star-rating")
    rating_class = [c for c in rating_elem["class"] if c != "star-rating"][0] if rating_elem else "Zero"
    
    # Description
    desc_elem = soup.select_one("#product_description ~ p")
    description = desc_elem.text.strip() if desc_elem else None

    raw_record = {
        "title": title,
        "product_url": book_url,
        "price_text": price_text,
        "price_gbp": parse_price(price_text),
        "availability_text": availability_text,
        "rating_text": rating_class,
        "rating_num": RATING_MAP.get(rating_class, 1),
        "description": description,
        "source_page": source_page,
        "fetched_at": datetime.now(timezone.utc).isoformat()
    }

    return raw_record, is_cached

# --- MAIN RUNNER PIPELINE ---
def run_pipeline():
    start_time = datetime.now(timezone.utc)
    logging.info("Starting Scraper Run...")

    # Stage 2: Discovery
    book_entries, cat_cache_hits = discover_books(max_pages=3)
    
    valid_records = []
    error_records = []
    detail_cache_hits = 0
    failed_pages = 0

    # Stage 3 & 4: Extract and Validate
    for idx, (book_url, source_page) in enumerate(book_entries, start=1):
        raw_data, is_cached = extract_book_details(book_url, source_page, idx)
        
        if is_cached:
            detail_cache_hits += 1

        if not raw_data:
            failed_pages += 1
            error_records.append({"url": book_url, "reason": "Failed page fetch or missing main content"})
            continue

        try:
            validated = BookSchema(**raw_data)
            valid_records.append(validated.model_dump(mode="json"))
        except ValidationError as ve:
            failed_pages += 1
            error_records.append({"url": book_url, "reason": str(ve)})

    # Write Outputs
    with open(os.path.join(OUTPUT_DIR, "books.json"), "w", encoding="utf-8") as f:
        json.dump(valid_records, f, indent=2, ensure_ascii=False)

    with open(os.path.join(OUTPUT_DIR, "errors.json"), "w", encoding="utf-8") as f:
        json.dump(error_records, f, indent=2)

    end_time = datetime.now(timezone.utc)
    duration_secs = round((end_time - start_time).total_seconds(), 2)

    # Stage 5: Run Report
    run_report = {
        "start_time": start_time.isoformat(),
        "duration_seconds": duration_secs,
        "catalogue_pages": 3,
        "discovered_urls": len(book_entries),
        "total_cache_hits": cat_cache_hits + detail_cache_hits,
        "valid_records": len(valid_records),
        "invalid_records": len(error_records),
        "failed_pages": failed_pages
    }

    with open(os.path.join(OUTPUT_DIR, "run-report.json"), "w", encoding="utf-8") as f:
        json.dump(run_report, f, indent=2)

    logging.info(f"Pipeline finished in {duration_secs}s. Scraped {len(valid_records)} valid records.")

if __name__ == "__main__":
    run_pipeline()