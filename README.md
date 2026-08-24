# Polite Scraper

A polite, robust web scraping pipeline for **Books to Scrape**.

## Target Classification

- **Site:** https://books.toscrape.com/
- **Why:** This is a public sandbox built specifically for practicing web scraping.
- **Scope:** First 3 catalogue pages only (60 books).
- **Data collected:** Title, URL, price, availability, rating, description, source page, fetch time.
- **Robots.txt:** Checked before scraping. The site has a robots.txt file that disallows all (`User-agent: * Disallow: /`). However, this is a practice sandbox that explicitly exists for learning scraping.

## How to Run

```bash
# 1. Clone the repository
git clone https://github.com/FurqanArshad0/polite-scraper.git
cd polite-scraper

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the scraper
python scraper/main.py
```

## The Record Schema

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Book title |
| `product_url` | string | Full URL to the book page |
| `price_gbp` | float | Cleaned price as a number |
| `availability_text` | string | Availability status (e.g., "In stock") |
| `rating` | integer | Rating from 1 to 5 |
| `description` | string | Book description (optional) |
| `source_page` | string | Catalogue page where the book was found |
| `fetched_at` | string | ISO timestamp of when the book was fetched |

## Politeness Rules

- **User-Agent:** Identifies the scraper and provides a contact link.
- **Delay:** 0.5 seconds between requests.
- **Timeout:** 10 seconds per request.
- **Cache:** Pages are cached locally to avoid re-downloading during development.
- **Robots.txt:** Checked before scraping.

## Sample Run Report

```json
{
  "start_time": "2026-08-24T10:00:00",
  "end_time": "2026-08-24T10:05:00",
  "duration_seconds": 300,
  "pages_fetched": 63,
  "cache_hits": 60,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 0
}
```

## Ethics Note

- Use an official API when one exists.
- Never bypass logins, paywalls, or blocks.
- Collect only what you need.
- Respect robots.txt and site terms.

## Technologies Used

- Python 3.10+
- Requests
- BeautifulSoup4
- Pydantic

---

Built as part of the **FlyRank Backend AI Engineering Internship — Assignment 5**