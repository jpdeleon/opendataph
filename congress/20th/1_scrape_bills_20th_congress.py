#!/usr/bin/env python
"""
NOTES

* This only scrapes the current (20th) congress.
* Number of bills indicated in the website is sometimes wrong.
For example, in https://econgress.gov.ph/house-members/?id=69&views=authoredbills,
"67 - Principal Authored Bills" is indicated but actually there are ony 51 unique bills in this page
based on bill code (e.g. HB06558).
"""
import time
import random
from pathlib import Path
from camoufox.sync_api import Camoufox
from playwright.sync_api import TimeoutError
from bs4 import BeautifulSoup
import pandas as pd
from tqdm import tqdm

def bypass_turnstile(page):
    """Try to click Cloudflare Turnstile if present."""
    page.wait_for_timeout(5_000)  # wait for Cloudflare to load
    try:
        page.mouse.click(210, 290)  # adjust coordinates if necessary
        if DEBUG:
            print("Clicked Turnstile checkbox")
        page.wait_for_load_state("networkidle")
        time.sleep(3)
    except Exception:
        print("Turnstile checkbox not found or already passed")

def get_member_info(soup):
    """Extract member name and representation (district or partylist)."""
    name = ""
    representation = ""

    name_span = soup.find("span", style=lambda x: x and "font-size:24px" in x)
    if name_span:
        name = name_span.get_text(strip=True)

    spans = soup.find_all("span", style=lambda x: x and "color:#365785" in x)
    if len(spans) > 1:
        raw_text = spans[1].get_text(" ", strip=True)
        if "|" in raw_text:
            part_a, part_b = map(str.strip, raw_text.split("|", 1))
            representation = f"{part_a} - {part_b}"
        else:
            representation = raw_text

    return name, representation
    
def get_authored_bills(page, member_id, house):
    """Fetch principal authored bills for a member."""
    url = f"{BASE_URL}/{house}/?id={member_id}&views=authoredbills"
    page.goto(url, timeout=60_000)

    # Try Cloudflare bypass
    bypass_turnstile(page)

    # Wait only for bill items
    try:
        page.wait_for_selector("ul.progress li.progress__item", timeout=8_000)
    except TimeoutError:
        print(f"Timeout waiting for bills for member {member_id}")
        return []

    soup = BeautifulSoup(page.content(), "html.parser")

    # Extract member info
    member_name, member_repr = get_member_info(soup)

    bills = []
    for li in soup.select("ul.progress li.progress__item"):
        code = li.find("p", class_="progress__title")
        infos = li.find_all("p", class_="progress__info")
        bill_code = code.get_text(strip=True) if code else ""
        bill_title = infos[0].get_text(strip=True) if len(infos) > 0 else ""
        bill_status = infos[1].get_text(strip=True) if len(infos) > 1 else ""
        
        bills.append({
            "member_id": member_id,
            "member_name": member_name,
            "representation": member_repr,
            "bill_code": bill_code,
            "bill_title": bill_title,
            "bill_status": bill_status
        })
    if DEBUG:
        # show only last bill
        print(f"{member_name} ({member_repr}) -> {bill_code}: {bill_title} [{bill_status}]")
    return bills

def scrape_congress_page(house):
    """
    Scrape legislator principal authored bills
    caveat: does not include info of previous members
    """
    assert house in ["senators", "house-members"]
    N_senators = 24 
    N_representatives = 312

    if house == "house-members": 
        first = 1
        last = N_representatives+1
    else:
        first = N_representatives+1 # id starts from 313
        last = N_representatives+N_senators+1
        
    member_ids = range(first, first+NDEBUG) if DEBUG else range(first, last)

    all_data = []
    with Camoufox(headless=HEADLESS, humanize=True, window=(1280, 720)) as browser:
        page = browser.new_page()
        bypass_turnstile(page)

        for mid in tqdm(member_ids, desc=f"Scraping {house}"):
            bills = []
            house_dir = Path(house)
            house_dir.mkdir(parents=True, exist_ok=True)  # create dir if missing
            fp = house_dir / f"{mid}.csv"
            
            if not fp.exists() or OVERWRITE:   
                print(f"Fetching bills for ID {mid}...")
                try:
                    bills = get_authored_bills(page, mid, house)

                    if len(bills) > 0:
                        write_header = not fp.exists()
                        df = pd.DataFrame(bills).drop_duplicates()#(subset='bill_code')
                        df.to_csv(fp, mode="a", header=write_header, index=False, encoding="utf-8-sig")
                except TimeoutError:
                    print(f"Timeout fetching bills for ID={mid}, skipping")
                except Exception as e:
                    print(f"Error fetching bills for ID={mid}: {e}")
            else:
                print(f"File exists. Skipping member id={mid}...")
                bills = pd.read_csv(fp).to_dict(orient="records")
                
            all_data.extend(bills)
            time.sleep(random.uniform(0.8,1.5)) # random wait time

        browser.close()
    df = pd.DataFrame(all_data).drop_duplicates()#(subset='bill_code')
    return df

def collate_and_save(house):
    # consolidate bills from all members
    files = Path(house).glob("*.csv")
    df = pd.concat(map(pd.read_csv, files), ignore_index=True)
    df = df.drop_duplicates()#(subset='bill_code')
    fp = f"{house}_bills"
    fp += "_test" if DEBUG else ""
    fp += ".csv"
    if not Path(fp).exists() or COLLATE:
        df.to_csv(fp, index=False, encoding="utf-8-sig")
        print("Saved: ", fp)
        
if __name__ == "__main__":
    #------global variables-----#
    BASE_URL = "https://econgress.gov.ph"
    DEBUG = False
    HEADLESS = not DEBUG # headless if not in debug mode
    NDEBUG = 2           # number of member id/pages to scrape if in debug mode
    OVERWRITE = False    # overwrite scraped bills per members
    COLLATE = True       # collate all saved bills per house
    #--------------------------#
    
    for house in ["senators", "house-members"]:
        df = scrape_congress_page(house) # used only for saving raw data
        print(df.head())
        print(df.shape)
        collate_and_save(house)

        # sanity check: 'Elizaldy S. Co' & 'Juan Edgardo "Sonny" Angara'
        mid = 69 if house=='house-members' else 320
        d = pd.read_csv(f'{house}/{mid}.csv').drop_duplicates()
        assert d.shape==df[df.member_id==mid].shape