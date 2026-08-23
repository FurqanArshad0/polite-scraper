import requests
from bs4 import BeautifulSoup
import os
import json
from datetime import datetime
import time
from urllib.parse import urljoin  


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

def main():
    print("Polite Scraper - Stage 2: Find All Pages")
    
    # Start with page 1
    base_url = "https://books.toscrape.com/catalogue/"
    current_url = "https://books.toscrape.com/catalogue/page-1.html"
    
    all_book_links = []
    page_number = 1
    
    while page_number <= 3 and current_url:
        print(f"\nProcessing page {page_number}: {current_url}")
        
        # Fetch the page (uses cache if available)
        html, from_cache = fetch_page(current_url)
        
        if not html:
            print(f"  Failed to load page {page_number}")
            break
        
        # Parse the HTML
        soup = get_soup(html)
        
        # Get book links from this page
        book_links = get_book_links(soup, base_url)
        print(f"  Found {len(book_links)} books on this page")
        all_book_links.extend(book_links)
        
        # Try to go to next page
        next_url = get_next_page_url(soup, current_url)
        if next_url:
            print(f"  Next page: {next_url}")
            current_url = next_url
            page_number += 1
        else:
            print("  No next page found")
            break
    
    # Remove duplicates (just in case)
    unique_links = list(set(all_book_links))
    
    print(f"\n{'='*50}")
    print(f"Summary:")
    print(f"  Pages processed: {page_number}")
    print(f"  Total books found: {len(all_book_links)}")
    print(f"  Unique books: {len(unique_links)}")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()