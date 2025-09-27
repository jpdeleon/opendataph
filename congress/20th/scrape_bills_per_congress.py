from camoufox import Camoufox
from bs4 import BeautifulSoup
import time
import random

def scrape_bills(congress=None):
    results = []

    with Camoufox(headless=HEADLESS, humanize=True, window=(1280, 720)) as browser:
        page = browser.new_page()

        for page_num in range(MAX_PAGES):
            # Build URL
            url = f"{BASE_URL}?sort_by=field_bill_date_of_filing_value&sort_order=DESC&items_per_page={ITEMS_PER_PAGE}&page={page_num}"
            if congress:
                url += f"&field_cn_bill_was_filed_target_id={congress}"

            print(f"Scraping page {page_num + 1}: {url}")
            page.goto(url)

            # Wait for content to load
            page.wait_for_selector("div.views-row", timeout=15000)  # wait up to 15s

            html = page.content()
            soup = BeautifulSoup(html, "html.parser")

            bills = soup.find_all("div", class_="views-row")
            if not bills:
                print("No more bills found. Exiting pagination.")
                break

            for bill in bills:
                # Long title
                long_title_tag = bill.find("span", class_="field-content")
                long_title = long_title_tag.get_text(strip=True) if long_title_tag else "N/A"

                # Short title (if present)
                short_title_tag = bill.find("div", class_="short-title")
                short_title = short_title_tag.get_text(strip=True) if short_title_tag else "N/A"

                # Author
                author_tag = bill.find("div", class_="field-name-field-author")
                author = author_tag.get_text(strip=True) if author_tag else "N/A"

                # Date filed
                date_tag = bill.find("span", class_="date-display-single")
                date_filed = date_tag.get_text(strip=True) if date_tag else "N/A"

                # Subjects
                subjects_tag = bill.find("div", class_="field-name-field-subjects")
                subjects = subjects_tag.get_text(strip=True) if subjects_tag else "N/A"

                # Link
                link_tag = bill.find("a")
                link = link_tag["href"] if link_tag else "N/A"

                results.append({
                    "long_title": long_title,
                    "short_title": short_title,
                    "author": author,
                    "date_filed": date_filed,
                    "subjects": subjects,
                    "link": link,
                })
            import pdb; pdb.set_trace()
            
            # Anti-bot random delay
            time.sleep(random.uniform(2, 5))

    return results

# Example usage
if __name__ == "__main__":
    # Settings
    HEADLESS = True
    BASE_URL = "https://ldr.senate.gov.ph/legislative-issuances/senate-bills"
    ITEMS_PER_PAGE = 100
    MAX_PAGES = 10  # limit to prevent overloading server

    bills_data = scrape_bills(congress=60488)  # e.g., 20th Congress
    for bill in bills_data:
        print(bill)