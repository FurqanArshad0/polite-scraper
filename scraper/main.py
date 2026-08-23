import requests
from bs4 import BeautifulSoup
import os
import json
from datetime import datetime
import time
from urllib.parse import urljoin

from requests.help import main  


# Configuration
USER_AGENT = "FlyRankInternship-PoliteScraper/1.0 (+https://github.com/FurqanArshad0/polite-scraper)"
TIMEOUT = 10
DELAY = 0.5
CACHE_DIR = "cache"
OUTPUT_DIR = "output"

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

def fetch_page(url, use_cache=True):
    filename = url.replace("https://", "").replace("/", "_").replace("?", "_")
    cache_path = os.path.join(CACHE_DIR, filename + ".html")
    
    if use_cache and os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            print(f"CACHE HIT: {url}")
            return f.read(), True
    
    print(f"FETCH: {url}")
    headers = {"User-Agent": USER_AGENT}
    
    try:
        response = requests.get(url, headers=headers, timeout=TIMEOUT)
        response.raise_for_status()
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(response.text)
        return response.text, False
    except requests.exceptions.RequestException as e:
        print(f"ERROR fetching {url}: {e}")
        return None, False
from urllib.parse import urljoin

def get_soup(html):
    """Parse HTML with BeautifulSoup."""
    return BeautifulSoup(html, "html.parser")

def get_book_links(soup, base_url):
    """
    Find all book links on a page.
    Returns: list of absolute URLs
    """
    links = []
    
    # Find all <a> tags that link to a book
    # In Books to Scrape, book links look like:
    # <a href="catalogue/a-light-in-the-attic_1000/index.html" title="...">
    for a_tag in soup.select("article.product_pod h3 a"):
        relative_url = a_tag.get("href")
        if relative_url:
            # Turn relative URL into absolute URL
            absolute_url = urljoin(base_url, relative_url)
            links.append(absolute_url)
    
    return links

def get_next_page_url(soup, base_url):
    """
    Find the URL of the next page.
    Returns: URL or None if no next page
    """
    # Find the "next" button
    next_link = soup.select_one("li.next a")
    if next_link:
        relative_url = next_link.get("href")
        return urljoin(base_url, relative_url)
    return None


# FUNCTION: extract_book_data
# What it does: Extract all book data from a single book page.


def get_text_safely(tag):
    """
    Safely extract text from a BeautifulSoup tag.
    Returns None if the tag doesn't exist.
    """
    if tag:
        return tag.string.strip() if tag.string else None
    return None

def extract_book_data(book_url, source_page):
    """
    Extract raw data from a book detail page.
    
    Parameters:
    - book_url: The URL of the book page
    - source_page: Where we found this book (catalogue page)
    
    Returns:
    - A dictionary with the extracted data
    """
    
    # Step 1: Fetch the book page (uses cache if available)
    html, from_cache = fetch_page(book_url)
    
    if not html:
        print(f"  ERROR: Could not fetch {book_url}")
        return None
    
    # Step 2: Parse the HTML
    soup = get_soup(html)
    
    # Step 3: Extract the title
    title_tag = soup.select_one("h1")
    title = get_text_safely(title_tag)
    
    # Step 4: Extract the price
    price_tag = soup.select_one("p.price_color")
    price_text = get_text_safely(price_tag)
    
    # Step 5: Extract availability — try multiple selectors
    avail_tag = soup.select_one("p.instock.availability")
    if not avail_tag:
        # Try alternative selector
        avail_tag = soup.select_one(".instock.availability")
    availability_text = get_text_safely(avail_tag)
    
    # Step 6: Extract rating
    rating_tag = soup.select_one("p.star-rating")
    rating_text = None
    if rating_tag:
        classes = rating_tag.get("class", [])
        for cls in classes:
            if cls != "star-rating":
                rating_text = cls
                break
    
    # Step 7: Extract description
    desc_tag = soup.select_one("#product_description ~ p")
    if not desc_tag:
        # Try alternative selector
        desc_tag = soup.select_one("div#product_description ~ p")
    description = get_text_safely(desc_tag)
    
    # Step 8: Build the raw record
    raw_record = {
        "title": title,
        "product_url": book_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": datetime.now().isoformat()
    }
    
    return raw_record

# ============================================================
# STAGE 4: Clean, Validate, Store
# ============================================================

# Import Pydantic for validation
from pydantic import BaseModel, ValidationError, Field
from typing import Optional

# ============================================================
# Define the clean data schema using Pydantic
# ============================================================

class BookRecord(BaseModel):
    """
    The shape of a clean, validated book record.
    Pydantic will automatically check every record against this schema.
    """
    title: str
    # title is required and must be a string
    
    product_url: str
    # product_url is required and must be a string
    
    price_gbp: float
    # price_gbp is required and must be a number (float)
    # This is the cleaned version of the price
    
    availability_text: Optional[str] = None
    # availability_text is optional (can be None)
    
    rating: int = Field(ge=1, le=5)
    # rating is required, must be between 1 and 5
    # ge=1 means "greater than or equal to 1"
    # le=5 means "less than or equal to 5"
    
    description: Optional[str] = None
    # description is optional (can be None)
    
    source_page: str
    # source_page is required
    
    fetched_at: str
    # fetched_at is required

# ============================================================
# FUNCTION: clean_price
# What it does: Turn "£51.77" into 51.77
# ============================================================

def clean_price(price_text):
    """
    Clean a price string into a number.
    
    Example: "Â£51.77" → 51.77
             "£51.77"   → 51.77
             "51.77"    → 51.77
    """
    if not price_text:
        return None
    
    # Remove the £ symbol and Â character
    cleaned = price_text.replace("Â", "").replace("£", "").strip()
    
    # Remove any extra spaces
    cleaned = cleaned.strip()
    
    try:
        # Convert to float (number with decimal)
        return float(cleaned)
    except ValueError:
        # If it can't be converted, return None
        return None

# ============================================================
# FUNCTION: clean_rating
# What it does: Turn "Three" into 3
# ============================================================

def clean_rating(rating_text):
    """
    Turn text rating into a number.
    
    Example: "One"   → 1
             "Two"   → 2
             "Three" → 3
             "Four"  → 4
             "Five"  → 5
    """
    if not rating_text:
        return None
    
    rating_map = {
        "One": 1,
        "Two": 2,
        "Three": 3,
        "Four": 4,
        "Five": 5
    }
    
    return rating_map.get(rating_text, None)
    # .get() returns None if the key doesn't exist

# ============================================================
# FUNCTION: clean_availability
# What it does: Extract just the availability status
# ============================================================

def clean_availability(availability_text):
    """
    Clean availability text.
    
    Example: "In stock (22 available)" → "In stock"
             "In stock"                 → "In stock"
    """
    if not availability_text:
        return None
    
    # If there's a parenthesis, take everything before it
    if "(" in availability_text:
        return availability_text.split("(")[0].strip()
    
    return availability_text.strip()

# ============================================================
# FUNCTION: clean_and_validate_record
# What it does: Take a raw record, clean it, validate it
# ============================================================

def clean_and_validate_record(raw_record):
    """
    Clean a raw record and validate it against the schema.
    
    Returns:
    - (clean_record, errors) where:
      - clean_record is a validated BookRecord or None
      - errors is a list of error messages or None
    """
    if not raw_record:
        return None, ["Empty record"]
    
    # Step 1: Clean the fields
    price_gbp = clean_price(raw_record.get("price_text"))
    rating = clean_rating(raw_record.get("rating_text"))
    availability = clean_availability(raw_record.get("availability_text"))
    
    # Step 2: Build a clean record dictionary
    clean_data = {
        "title": raw_record.get("title"),
        "product_url": raw_record.get("product_url"),
        "price_gbp": price_gbp,
        "availability_text": availability,
        "rating": rating,
        "description": raw_record.get("description"),
        "source_page": raw_record.get("source_page"),
        "fetched_at": raw_record.get("fetched_at")
    }
    
    # Step 3: Validate against the schema
    try:
        validated = BookRecord(**clean_data)
        return validated, None
    except ValidationError as e:
        # Pydantic caught errors — return the error messages
        errors = [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
        return None, errors

# ============================================================
# FUNCTION: save_clean_records
# What it does: Save clean records to books.json
# ============================================================

def save_clean_records(valid_records, errors):
    """
    Save valid records to books.json and errors to errors.json
    """
    # Save valid records
    books_path = os.path.join(OUTPUT_DIR, "books.json")
    with open(books_path, "w", encoding="utf-8") as f:
        # Convert each record to a dictionary for JSON
        records_dict = [record.dict() for record in valid_records]
        json.dump(records_dict, f, indent=2, ensure_ascii=False)
    
    # Save errors if any
    if errors:
        errors_path = os.path.join(OUTPUT_DIR, "errors.json")
        with open(errors_path, "w", encoding="utf-8") as f:
            json.dump(errors, f, indent=2, ensure_ascii=False)
            
            
def main():
    print("Polite Scraper - Stage 4: Clean, Validate, Store")
    
    # Step 1: Load raw records from Stage 3
    raw_path = os.path.join(OUTPUT_DIR, "raw_records.json")
    
    if not os.path.exists(raw_path):
        print("ERROR: raw_records.json not found. Run Stage 3 first.")
        return
    
    with open(raw_path, "r", encoding="utf-8") as f:
        raw_records = json.load(f)
    
    print(f"Loaded {len(raw_records)} raw records from {raw_path}")
    
    # Step 2: Clean and validate each record
    valid_records = []
    error_records = []
    
    for i, raw_record in enumerate(raw_records, 1):
        print(f"\nProcessing record {i}/{len(raw_records)}: {raw_record.get('title', 'No title')[:40]}...")
        
        clean_record, errors = clean_and_validate_record(raw_record)
        
        if clean_record:
            valid_records.append(clean_record)
            print(f"  ✅ Valid: {clean_record.title[:40] if clean_record.title else 'No title'}...")
            print(f"     Price: £{clean_record.price_gbp}, Rating: {clean_record.rating}")
        else:
            error_records.append({
                "raw_record": raw_record,
                "errors": errors
            })
            print(f"   Invalid: {errors}")
    
    # Step 3: Save the results
    save_clean_records(valid_records, error_records)
    
    # Step 4: Print summary
    print(f"\n{'='*50}")
    print(f"Summary:")
    print(f"  Raw records loaded: {len(raw_records)}")
    print(f"  Valid records: {len(valid_records)}")
    print(f"  Invalid records: {len(error_records)}")
    print(f"  Clean data saved to: {os.path.join(OUTPUT_DIR, 'books.json')}")
    if error_records:
        print(f"  Errors saved to: {os.path.join(OUTPUT_DIR, 'errors.json')}")
    print(f"{'='*50}")
    
    
    
if __name__ == "__main__":
    main()