import requests
from bs4 import BeautifulSoup
import os
import json
from datetime import datetime
import time
from urllib.parse import urljoin
from pydantic import BaseModel, ValidationError, Field
from typing import Optional

USER_AGENT = "FlyRankInternship-PoliteScraper/1.0 (+https://github.com/FurqanArshad0/polite-scraper)"
TIMEOUT = 10
DELAY = 0.5
CACHE_DIR = "cache"
OUTPUT_DIR = "output"

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ========== Helper for Safe Text Extraction ==========
def get_text_safely(tag):
    if tag:
        return tag.string.strip() if tag.string else None
    return None

# ========== Fetch & Cache ==========
def fetch_page(url, use_cache=True, retry_count=1):
    filename = url.replace("https://", "").replace("/", "_").replace("?", "_")
    cache_path = os.path.join(CACHE_DIR, filename + ".html")
    
    if use_cache and os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            print(f"CACHE HIT: {url}")
            return f.read(), True, True
    
    print(f"FETCH: {url}")
    headers = {"User-Agent": USER_AGENT}
    
    for attempt in range(retry_count + 1):
        try:
            response = requests.get(url, headers=headers, timeout=TIMEOUT)
            response.raise_for_status()
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(response.text)
            return response.text, False, True
        except requests.exceptions.RequestException as e:
            if attempt < retry_count:
                print(f"  Retry {attempt + 1}/{retry_count}: {e}")
                time.sleep(2)
            else:
                print(f"  ERROR after {retry_count + 1} attempts: {e}")
                return None, False, False

# ========== HTML Parsing Helpers ==========
def get_soup(html):
    return BeautifulSoup(html, "html.parser")

def get_book_links(soup, base_url):
    links = []
    for a_tag in soup.select("article.product_pod h3 a"):
        relative_url = a_tag.get("href")
        if relative_url:
            absolute_url = urljoin(base_url, relative_url)
            links.append(absolute_url)
    return links

def get_next_page_url(soup, current_url):
    next_link = soup.select_one("li.next a")
    if next_link:
        return urljoin(current_url, next_link.get("href"))
    return None

# ========== Cleaners ==========
def clean_price(price_text):
    if not price_text:
        return None
    cleaned = price_text.replace("Â", "").replace("£", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None

def clean_rating(rating_text):
    if not rating_text:
        return None
    rating_map = {
        "One": 1, "Two": 2, "Three": 3,
        "Four": 4, "Five": 5
    }
    return rating_map.get(rating_text, None)

def clean_availability(availability_text):
    if not availability_text:
        return None
    if "(" in availability_text:
        return availability_text.split("(")[0].strip()
    return availability_text.strip()

# ========== Schema ==========
class BookRecord(BaseModel):
    title: str
    product_url: str
    price_gbp: float
    availability_text: Optional[str] = None
    rating: int = Field(ge=1, le=5)
    description: Optional[str] = None
    source_page: str
    fetched_at: str

# ========== Validate ==========
def clean_and_validate_record(raw_record):
    if not raw_record:
        return None, ["Empty record"]
    
    clean_data = {
        "title": raw_record.get("title"),
        "product_url": raw_record.get("product_url"),
        "price_gbp": clean_price(raw_record.get("price_text")),
        "availability_text": clean_availability(raw_record.get("availability_text")),
        "rating": clean_rating(raw_record.get("rating_text")),
        "description": raw_record.get("description"),
        "source_page": raw_record.get("source_page"),
        "fetched_at": raw_record.get("fetched_at")
    }
    
    try:
        validated = BookRecord(**clean_data)
        return validated, None
    except ValidationError as e:
        errors = [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
        return None, errors

# ========== Save ==========
def save_clean_records(valid_records, errors):
    books_path = os.path.join(OUTPUT_DIR, "books.json")
    with open(books_path, "w", encoding="utf-8") as f:
        records_dict = [record.dict() for record in valid_records]
        json.dump(records_dict, f, indent=2, ensure_ascii=False)
    
    if errors:
        errors_path = os.path.join(OUTPUT_DIR, "errors.json")
        with open(errors_path, "w", encoding="utf-8") as f:
            json.dump(errors, f, indent=2, ensure_ascii=False)

# ========== Report ==========
def generate_report(start_time, end_time, stats):
    duration = (end_time - start_time).total_seconds()
    report = {
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "duration_seconds": duration,
        "pages_fetched": stats.get("pages_fetched", 0),
        "cache_hits": stats.get("cache_hits", 0),
        "valid_records": stats.get("valid_records", 0),
        "invalid_records": stats.get("invalid_records", 0),
        "failed_pages": stats.get("failed_pages", 0)
    }
    report_path = os.path.join(OUTPUT_DIR, "run-report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return report

# ========== Main ==========
def main():
    print("Polite Scraper - Stage 5: Survive Failures, Report the Run")
    
    start_time = datetime.now()
    stats = {
        "pages_fetched": 0,
        "cache_hits": 0,
        "valid_records": 0,
        "invalid_records": 0,
        "failed_pages": 0
    }
    
    base_url = "https://books.toscrape.com/catalogue/"
    start_url = "https://books.toscrape.com/catalogue/page-1.html"
    
    all_book_links = []
    page_number = 1
    current_url = start_url
    
    while page_number <= 3 and current_url:
        print(f"\nCollecting links from page {page_number}...")
        html, from_cache, success = fetch_page(current_url)
        stats["pages_fetched"] += 1
        if from_cache:
            stats["cache_hits"] += 1
        
        if not success:
            stats["failed_pages"] += 1
            break
        
        soup = get_soup(html)
        book_links = get_book_links(soup, base_url)
        all_book_links.extend(book_links)
        print(f"  Found {len(book_links)} books on this page")
        
        next_url = get_next_page_url(soup, current_url)
        if next_url:
            current_url = next_url
            page_number += 1
        else:
            break
    
    unique_links = list(set(all_book_links))
    print(f"\nTotal unique books to process: {len(unique_links)}")
    
    raw_records = []
    
    for i, book_url in enumerate(unique_links, 1):
        print(f"\nProcessing book {i}/{len(unique_links)}: {book_url}")
        
        html, from_cache, success = fetch_page(book_url)
        stats["pages_fetched"] += 1
        if from_cache:
            stats["cache_hits"] += 1
        
        if not success:
            stats["failed_pages"] += 1
            print(f"  SKIPPED: Failed to fetch page")
            continue
        
        soup = get_soup(html)
        
        title_tag = soup.select_one("h1")
        title = get_text_safely(title_tag)
        
        price_tag = soup.select_one("p.price_color")
        price_text = get_text_safely(price_tag)
        
        avail_tag = soup.select_one("p.instock.availability")
        if not avail_tag:
            avail_tag = soup.select_one(".instock.availability")
        availability_text = get_text_safely(avail_tag)
        
        if not availability_text:
            availability_text = "In stock"
        
        rating_tag = soup.select_one("p.star-rating")
        rating_text = None
        if rating_tag:
            for cls in rating_tag.get("class", []):
                if cls != "star-rating":
                    rating_text = cls
                    break
        
        desc_tag = soup.select_one("#product_description ~ p")
        description = get_text_safely(desc_tag)
        
        raw_record = {
            "title": title,
            "product_url": book_url,
            "price_text": price_text,
            "availability_text": availability_text,
            "rating_text": rating_text,
            "description": description,
            "source_page": "https://books.toscrape.com/catalogue/",
            "fetched_at": datetime.now().isoformat()
        }
        
        raw_records.append(raw_record)
        print(f"  Title: {title[:50] if title else 'None'}...")
        print(f"  Price: {price_text}")
        print(f"  Rating: {rating_text}")
        
        time.sleep(DELAY)
    
    raw_path = os.path.join(OUTPUT_DIR, "raw_records.json")
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(raw_records, f, indent=2, ensure_ascii=False)
    
    valid_records = []
    error_records = []
    
    for raw_record in raw_records:
        clean_record, errors = clean_and_validate_record(raw_record)
        if clean_record:
            valid_records.append(clean_record)
        else:
            error_records.append({"raw_record": raw_record, "errors": errors})
    
    stats["valid_records"] = len(valid_records)
    stats["invalid_records"] = len(error_records)
    
    save_clean_records(valid_records, error_records)
    
    end_time = datetime.now()
    report = generate_report(start_time, end_time, stats)
    
    print(f"\n{'='*50}")
    print(f"Summary:")
    print(f"  Pages fetched: {stats['pages_fetched']}")
    print(f"  Cache hits: {stats['cache_hits']}")
    print(f"  Valid records: {stats['valid_records']}")
    print(f"  Invalid records: {stats['invalid_records']}")
    print(f"  Failed pages: {stats['failed_pages']}")
    print(f"  Duration: {report['duration_seconds']:.2f} seconds")
    print(f"  Clean data saved to: {os.path.join(OUTPUT_DIR, 'books.json')}")
    print(f"  Report saved to: {os.path.join(OUTPUT_DIR, 'run-report.json')}")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()