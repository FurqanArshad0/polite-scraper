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
def main():
    print("Polite Scraper - Stage 3: Extract Raw Book Data")
    
    # Step 1: Get all book URLs from Stage 2
    base_url = "https://books.toscrape.com/catalogue/"
    start_url = "https://books.toscrape.com/catalogue/page-1.html"
    
    all_book_links = []
    page_number = 1
    current_url = start_url
    
    # Collect all book URLs
    while page_number <= 3 and current_url:
        print(f"\nCollecting links from page {page_number}...")
        html, from_cache = fetch_page(current_url)
        if not html:
            print(f"  Failed to load page {page_number}")
            break
        
        soup = get_soup(html)
        book_links = get_book_links(soup, base_url)
        print(f"  Found {len(book_links)} books on this page")
        all_book_links.extend(book_links)
        
        next_url = get_next_page_url(soup, current_url)
        if next_url:
            current_url = next_url
            page_number += 1
        else:
            break
    
    unique_links = list(set(all_book_links))
    print(f"\nTotal unique books to process: {len(unique_links)}")
    
    # Step 2: Process each book
    raw_records = []
    processed = 0
    
    for book_url in unique_links:
        processed += 1
        print(f"\nProcessing book {processed}/{len(unique_links)}: {book_url}")
        
        # IMPORTANT: Store the source page for this book
        # Since we don't track which page each book came from, we use the base URL
        record = extract_book_data(book_url, "https://books.toscrape.com/catalogue/")
        
        if record:
            raw_records.append(record)
            print(f"  Title: {record['title'][:50] if record['title'] else 'None'}")
            print(f"  Price: {record['price_text']}")
            print(f"  Rating: {record['rating_text']}")
        else:
            print(f"  SKIPPED: Could not extract data")
        
        # Be polite — wait between requests
        time.sleep(DELAY)
    
    # Step 3: Save raw records to a file
    output_path = os.path.join(OUTPUT_DIR, "raw_records.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(raw_records, f, indent=2, ensure_ascii=False)
    
    # Step 4: Print summary
    print(f"\n{'='*50}")
    print(f"Summary:")
    print(f"  Books processed: {processed}")
    print(f"  Records extracted: {len(raw_records)}")
    print(f"  Records with title: {sum(1 for r in raw_records if r['title'])}")
    print(f"  Records with price: {sum(1 for r in raw_records if r['price_text'])}")
    print(f"  Raw data saved to: {output_path}")
    print(f"{'='*50}")
    
    
    
if __name__ == "__main__":
    main()