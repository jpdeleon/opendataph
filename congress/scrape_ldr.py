#!/usr/bin/env python
"""
Scrape all Senate bills per Congress and save incrementally.
"""
import time
import random
from pathlib import Path
from camoufox.sync_api import Camoufox
from playwright.sync_api import TimeoutError
from bs4 import BeautifulSoup
import pandas as pd
import re
from tqdm import tqdm

# -------------------------------
# MANUAL CONGRESS IDS
# -------------------------------
congress_dict = {
    13: 46,
    14: 47,
    15: 48,
    16: 240,
    17: 53,
    18: 220,
    19: 60488,
    20: 68805,
}

# -------------------------------
# UTILITY FUNCTIONS
# -------------------------------
def get_total_pages(soup):
    """Determine total pages from the 'Displaying X of Y' text."""
    header_tag = soup.select_one("div.view-header")
    total_bills = 0
    if header_tag:
        text = header_tag.get_text(strip=True)
        match = re.search(r"of\s+(\d+)", text)
        if match:
            total_bills = int(match.group(1))
    total_pages = (total_bills + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    return total_pages

def scrape_bills_page(page, congress_id, page_num):
    """Scrape bills from a single page."""
    url = (
        f"{BASE_URL}?"
        f"field_date_of_approval_value=All&"
        f"field_cn_bill_was_filed_target_id={congress_id}&"
        f"sort_by=title&"
        f"sort_order=DESC&"
        f"items_per_page={ITEMS_PER_PAGE}&"
        f"page={page_num}"
    )
    page.goto(url)
    try:
        page.wait_for_selector("article[role='article']", timeout=15_000)
    except TimeoutError:
        print(f"Timeout waiting for page {page_num} of Congress {congress_id}")
        return []

    soup = BeautifulSoup(page.content(), "html.parser")
    articles = soup.select("article[role='article']")

    bills = []
    for article in articles:
        link_tag = article.select_one("h2 a")
        link = "https://ldr.senate.gov.ph" + link_tag["href"] if link_tag else "N/A"

        long_title_tag = article.select_one(".field--name-field-long-title .field__item")
        long_title = long_title_tag.get_text(strip=True) if long_title_tag else "N/A"

        short_title_tag = article.select_one(".field--name-field-short-title .field__item")
        short_title = short_title_tag.get_text(strip=True) if short_title_tag else "N/A"

        author_tags = article.select(".field--name-field-author .field__item a")
        authors = "; ".join([a.get_text(strip=True) for a in author_tags]) if author_tags else "N/A"

        date_tag = article.select_one(".field--name-field-bill-date-of-filing .field__item")
        date_filed = date_tag.get_text(strip=True) if date_tag else "N/A"

        subject_tags = article.select(".field--name-field-subjects .field__item a")
        subjects = "; ".join([s.get_text(strip=True) for s in subject_tags]) if subject_tags else "N/A"

        bills.append({
            "congress_id": congress_id,
            "link": link,
            "long_title": long_title,
            "short_title": short_title,
            "authors": authors,
            "date_filed": date_filed,
            "subjects": subjects
        })
    return bills

# -------------------------------
# MAIN SCRAPING FUNCTION
# -------------------------------
def scrape_congress_bills(house):
    all_data = []
    with Camoufox(headless=HEADLESS, humanize=True, window=(1280, 720)) as browser:
        page = browser.new_page()

        for congress_number, congress_id in congress_dict.items():
            congress_name = f"{congress_number}th_Congress"
            print(f"\nScraping {congress_name} (ID={congress_id})...")

            dir_path = Path(f"{house}_bills") / congress_name
            dir_path.mkdir(parents=True, exist_ok=True)
            fp = dir_path / "bills.csv"

            # First page to determine total pages

            url = ( f"{BASE_URL}?"
                f"field_date_of_approval_value=All&"
                f"field_cn_bill_was_filed_target_id={congress_id}&"
                f"sort_by=title&"
                f"sort_order=DESC&"
                f"items_per_page={ITEMS_PER_PAGE}&"
                # f"page={page_num}"
            )
            print(url)
            page.goto(url)
            
            try:
                page.wait_for_selector("div.view-header", timeout=15_000)
                soup = BeautifulSoup(page.content(), "html.parser")
                total_pages = get_total_pages(soup)
                if DEBUG:
                    total_pages = min(NDEBUG, total_pages)
                print(f"{total_pages} pages to scrape for {congress_name}")
            except TimeoutError:
                print(f"No bills found or page layout different for {congress_name} (ID={congress_id}), skipping...")
                continue  # skip to next congress

            for page_num in tqdm(range(total_pages), desc=f"Scraping {congress_name}"):
                bills = scrape_bills_page(page, congress_id, page_num)
                if bills:
                    write_header = not fp.exists() or OVERWRITE
                    df = pd.DataFrame(bills)
                    df.to_csv(fp, mode="a", header=write_header, index=False, encoding="utf-8-sig")
                    all_data.extend(bills)
                time.sleep(random.uniform(0.8, 1.5))

    # Collate all into single CSV
    if COLLATE:
        all_files = list(Path(f"{house}_bills").glob("**/bills.csv"))
        df_all = pd.concat([pd.read_csv(f) for f in all_files], ignore_index=True)
        df_all.drop_duplicates(inplace=True)
        out_fp = f"{house}_bills_all.csv"
        df_all.to_csv(out_fp, index=False, encoding="utf-8-sig")
        print(f"Saved collated CSV: {out_fp}")

    return pd.DataFrame(all_data)

# -------------------------------
# ENTRY POINT
# -------------------------------
if __name__ == "__main__":
    # ---------CONFIG---------
    ITEMS_PER_PAGE = 100
    OVERWRITE = False
    COLLATE = True
    DEBUG = False
    HEADLESS = not DEBUG
    NDEBUG = 2  # number of pages to scrape if DEBUG
    # -------------------------------

    for house in ['house', #'senate',
                 ]:
        BASE_URL = f"https://ldr.senate.gov.ph/legislative-issuances/{house}-bills"
        df = scrape_congress_bills(house)
        print(df.head())
        print(f"Total bills scraped: {df.shape[0]}")