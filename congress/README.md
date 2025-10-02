Got it 👍 — here’s a **README.md** you can drop into your project folder. It explains both scrapers (Senate and House from `ldr.senate.gov.ph`, plus `congress.gov.ph` if you extend it), how to run them, and how the outputs are organized.

---

# 📜 Philippine Legislative Bills Scraper

This repository contains Python scripts to scrape **Philippine legislative data** from publicly available sources:

* **Senate Bills** and **House Bills** from [LDR Senate](https://ldr.senate.gov.ph/legislative-issuances)
* (Optional) Bills from [eCongress](https://www.econgress.gov.ph/) if extended

The scripts incrementally collect all bills per **Congress session**, save them into CSV files, and collate them into a single dataset for analysis.

---

## ⚙️ Requirements

* Python **3.10+**
* [Camoufox](https://pypi.org/project/camoufox/) (Playwright wrapper with anti-bot support)
* Playwright (for browser automation)
* BeautifulSoup4
* pandas
* tqdm
* re (standard library)
* time / random (standard library)

Install dependencies:

```bash
pip install camoufox playwright beautifulsoup4 pandas tqdm
playwright install
```

---

## 📂 Repository Structure

```
project/
│
├── scrape_senate_bills.py        # Scrapes Senate bills per Congress
├── scrape_house_bills.py         # Scrapes House bills per Congress
├── utils/                        # (Optional) shared helpers
├── senate_bills/                 # Incremental Senate outputs per Congress
│   └── 19th_Congress/bills.csv
├── house_bills/                  # Incremental House outputs per Congress
│   └── 19th_Congress/bills.csv
├── senate_bills_all.csv          # Collated Senate bills
├── house_bills_all.csv           # Collated House bills
└── README.md                     # You are here
```

---

## 🏛️ Congress Mapping

Both Senate and House scripts rely on a **manual mapping** between `congress_id` (internal LDR identifiers) and **Congress number**:

```python
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
```

* Keys = Congress number (13th → 20th)
* Values = LDR `field_cn_bill_was_filed_target_id`

---

## 🚀 Usage

### 1. Scraping Senate Bills

Run:

```bash
python scrape_senate_bills.py
```

* Creates `senate_bills/<Congress>/bills.csv` per Congress
* Collates into `senate_bills_all.csv`

### 2. Scraping House Bills

Run:

```bash
python scrape_house_bills.py
```

* Creates `house_bills/<Congress>/bills.csv` per Congress
* Collates into `house_bills_all.csv`

---

## 🔍 Configuration

Inside each script:

```python
ITEMS_PER_PAGE = 100    # max items per page
OVERWRITE = False       # append to CSVs or overwrite
COLLATE = True          # whether to collate into *_all.csv
DEBUG = False           # set True to limit scraping (uses NDEBUG pages only)
HEADLESS = not DEBUG    # headless browser unless debugging
```

---

## 📊 Output Columns

Each scraped bill has:

* `congress_id` – numeric LDR identifier
* `congress_number` – mapped 13–20
* `link` – official bill page URL
* `long_title` – full descriptive title
* `short_title` – short/formal title
* `authors` – list of authors (semicolon separated)
* `date_filed` – filing date (string)
* `subjects` – subjects/tags (semicolon separated)

---

## 🧩 Next Steps

After scraping, you can:

* Perform **feature engineering** (themes, bill types, committees, etc.)
* Build **dashboards** (e.g., Plotly, Dash, Streamlit)
* Export to **interactive HTML tables** for exploration
* Apply **NLP / LLMs** to classify and summarize bills

---

## ⚠️ Disclaimer

This project is for **research and educational purposes only**.
Respect the source websites’ [Terms of Use](https://ldr.senate.gov.ph/) and avoid excessive requests.

---

