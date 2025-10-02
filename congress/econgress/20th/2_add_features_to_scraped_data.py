#!/usr/bin/env python
"""
Process bills CSV for a specific Congress and chamber (House/Senate).
Adds derived features: themes, primary theme, status normalization, dates,
URLs, bill age, success rate, competition index, committee info, and more.

Outputs a processed DataFrame ready for analysis or visualization.

| Column Name           | Description                                                                                  | Example                                                            |
| --------------------- | -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| `bill_code`           | Original code from CSV; includes prefix + number.                                            | `HB04102`, `SB1175`                                                |
| `bill_type`           | Letter prefix part of `bill_code`; indicates chamber or type.                                | `HB`, `SB`                                                         |
| `bill_number`         | Numeric part of `bill_code`; the sequential number of the bill.                              | `4102`, `1175`                                                     |
| `res_type`            | Generalized type for URL construction (`HB`, `SB`, `SRN`, etc.).                             | `HB`, `SB`                                                         |
| `res_number`          | Numeric ID for URL construction; same as `bill_number`.                                      | `4102`, `1175`                                                     |
| `bill_title`          | Full title of the bill/resolution.                                                           | “AN ACT …”                                                         |
| `theme`               | List of thematic categories assigned from keywords.                                          | `[Economy]`                                                        |
| `primary_theme`       | First theme in list, for visualization or grouping.                                          | `Economy`                                                          |
| `bill_status_str`     | Original status text from CSV.                                                               | “Approved by the House on 2022-11-14, transmitted to Senate…”      |
| `bill_status`         | Normalized status (`Pending`, `Passed`, `Rejected`, `Other`, `Unknown`).                     | `Passed`                                                           |
| `status_date`         | Earliest date parsed from `bill_status_str` or CSV.                                          | `2022-11-14`                                                       |
| `bill_age_days`       | Number of days since `status_date` (only for bills not yet passed).                          | `120`                                                              |
| `num_status_changes`  | Number of times the status text indicates a change or action (proxy via commas/semicolons).  | `3`                                                                |
| `congress_number`     | Congress session the bill belongs to, derived from `status_date`.                            | `19`                                                               |
| `member_success_rate` | Percentage of bills passed per member.                                                       | `0.75`                                                             |
| `member_theme_focus`  | Most frequent primary theme filed by the member.                                             | `Economy`                                                          |
| `competition_index`   | Number of bills on the same theme within the same Congress (how crowded the policy area is). | `25`                                                               |
| `committee`           | Committee name extracted from `bill_status_str` if mentioned.                                | `Committee on WAYS & MEANS`                                        |
| `committee_overlap`   | Number of unique members filing bills in the same committee.                                 | `4`                                                                |
| `chamber_lag_days`    | Number of days between House approval and Senate reception.                                  | `1`                                                                |
| `resolution_url`      | Link to official bill/resolution page based on type, number, and congress.                   | `https://ldr.senate.gov.ph/bills/house-bill-no-4102-19th-congress` |

"""
#!/usr/bin/env python3
import pandas as pd
import re
import numpy as np

def extract_clean_words(text):
    """Return lowercase alphabetic words of length >=2 from text."""
    text = str(text).lower()
    return re.findall(r'\b[a-z]{2,}\b', text)

def assign_themes(title):
    """Assign themes to a bill title based on keywords."""
    title_words = extract_clean_words(title)
    matched = {theme for theme, kws in theme_keywords.items() if any(w in kws for w in title_words)}
    return tuple(sorted(matched)) if matched else ("Other",)

def assign_status(status_text):
    """Normalize status strings to standard categories."""
    if pd.isna(status_text) or status_text.strip() == "Unknown":
        return "Unknown"
    st = status_text.lower()
    if "pending" in st: return "Pending"
    if "consolidated" in st or "substituted" in st: return "Consolidated/Substituted"
    if "approved" in st or "passed" in st: return "Passed"
    if "rejected" in st: return "Rejected"
    return "Other"

def assign_bill_action(row):
    """Classify bill into action types based on status and title."""
    status = str(row['bill_status_str']).lower()
    title = str(row['bill_title']).lower()

    # New Bill
    if "act" in title or "bill" in title:
        action = "New Bill"
    
    # Amendment / Revision
    if any(word in title for word in ["amending", "repeal", "revision", "reforming"]):
        action = "Amendment"

    # Consolidated / Substituted
    if "consolidated" in status or "substituted" in status:
        action = "Consolidated/Substituted"

    # Expressions / Resolutions
    if "resolution" in title or "expressing" in title or "commending" in title:
        action = "Resolution/Expression"

    # If none of the above, default to Other
    if 'action' not in locals():
        action = "Other"

    return action
    
def parse_status_date(row):
    """Extract earliest date from bill_status_str if status_date is missing."""
    if pd.notna(row.get('status_date')): return row['status_date']
    status_text = str(row.get('bill_status_str', ''))
    dates = re.findall(r'\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}', status_text)
    if not dates: return pd.NaT
    parsed = pd.to_datetime(dates, errors='coerce')
    parsed = parsed[parsed.notna()]
    return parsed.min() if not parsed.empty else pd.NaT

def parse_bill_code(code):
    """Split bill code into type and number, e.g., HB04102 -> (HB, 4102)."""
    match = re.match(r'([A-Z]+)[-]?(\d+)', str(code))
    if match:
        return match.group(1).upper(), int(match.group(2))
    return None, None

def map_congress(date):
    """Map a date to Congress number."""
    if pd.isna(date): return None
    if pd.Timestamp('2022-07-25') <= date <= pd.Timestamp('2025-06-30'): return 19
    if pd.Timestamp('2019-07-22') <= date <= pd.Timestamp('2022-06-30'): return 18
    if pd.Timestamp('2016-07-25') <= date <= pd.Timestamp('2019-06-30'): return 17
    return None

def get_chamber_lag(status_text):
    """Return days between House and Senate action from status text."""
    dates = re.findall(r'\d{4}-\d{2}-\d{2}', str(status_text))
    if len(dates) >= 2:
        try:
            return (pd.to_datetime(dates[1]) - pd.to_datetime(dates[0])).days
        except: return np.nan
    return np.nan

def compute_member_theme_focus(df):
    """Return most frequent primary theme per member."""
    counts = df.groupby(['member_name', 'primary_theme']).size().reset_index(name='count')
    idx = counts.groupby('member_name')['count'].idxmax()
    return pd.Series(dict(zip(counts.loc[idx, 'member_name'], counts.loc[idx, 'primary_theme'])))

def compute_committee_overlap(df):
    """Count unique members filing bills in the same committee."""
    df = df.copy()
    df['committee'] = df['bill_status_str'].str.extract(r'Committee on ([A-Z &]+)')
    return df.groupby('committee')['member_name'].transform('nunique')

def add_member_profile_url(df, house):
    """Add member profile URL based on member_id and house."""
    base_url = "https://www.econgress.gov.ph"
    df['member_profile_url'] = df['member_id'].apply(
        lambda mid: f"{base_url}/{house}/?id={mid}&views=authoredbills"
    )
    return df

def make_ldr_url(res_type, res_number, congress_number):
    """Generate official LDR/House bill URL based on type and number."""
    if pd.isna(res_type) or pd.isna(res_number) or pd.isna(congress_number): return np.nan
    congress_str = f"{int(congress_number)}th-congress"
    if res_type.upper() in ['SB', 'SRN']:
        return f"https://ldr.senate.gov.ph/legislative-issuance/{res_type}-{res_number}-{congress_str}"
    if res_type.upper() == 'HB':
        return f"https://ldr.senate.gov.ph/bills/house-bill-no-{res_number}-{congress_str}"
    return np.nan

theme_keywords = {
    "Health": ["hospital", "medical", "nurse", "health", "care", "pharmacy", "vaccine"],
    "Education": ["school", "student", "teacher", "university", "education", "academy", "learning"],
    "Environment": ["environment", "reforestation", "wildlife", "forest", "climate", "renewable", "water"],
    "Transport": ["road", "transport", "vehicle", "motorcycle", "traffic", "highway", "public", "commute"],
    "Governance": ["government", "department", "administrative", "policy", "bureau", "regulation", "law"],
    "Economy": ["business", "industry", "commerce", "economic", "tax", "labor", "employment"],
    "Disaster/Resilience": ["disaster", "risk", "emergency", "evacuation", "safety", "protection", "calamity"],
    }

# ---------------------------
# Main Processing
# ---------------------------
def main():
    #congress_number='20th'
    for house in ["senators", "house-members"]:

        # ---------------------------
        # Data Cleaning Functions
        # ---------------------------    
        # Configuration
        df = pd.read_csv(f'{house}_bills.csv').drop_duplicates(by='bill_code')
        df = df.rename({'bill_status': 'bill_status_str'}, axis=1)
        
        # Member profile URLs
        df = add_member_profile_url(df, house)
        
        # Themes
        df['theme'] = df['bill_title'].apply(assign_themes)
        df['primary_theme'] = df['theme'].apply(lambda x: x[0] if isinstance(x, tuple) else "Other")
        
        # Bill codes
        df['res_type'], df['res_number'] = zip(*df['bill_code'].map(parse_bill_code))
        df['bill_type'] = df['bill_code'].str.extract(r'([A-Z]+)')[0]

        # df['bill_action_type'] = df.apply(assign_bill_action, axis=1)
        
        # Dates and status
        df['status_date'] = df.apply(parse_status_date, axis=1)
        df['bill_status'] = df['bill_status_str'].apply(assign_status).fillna('Unknown')
        df['congress_number'] = df['status_date'].apply(map_congress)
        df['year'] = df['status_date'].dt.year.astype('Int64')
        
        # Bill age
        date_today = pd.Timestamp.today()
        df['bill_age_days'] = np.where(df['bill_status'] != 'Passed',
                                       (date_today - df['status_date']).dt.days,
                                       np.nan)
        
        # Committee and status changes
        df['committee'] = df['bill_status_str'].str.extract(r'Committee on ([A-Z &]+)')
        df['num_status_changes'] = df['bill_status_str'].str.count(r',|;| and ') + 1
        
        # Member statistics
        member_stats = df.groupby('member_name')['bill_status'].value_counts(normalize=True).unstack(fill_value=0)
        df['member_success_rate'] = df['member_name'].map(member_stats.get('Passed', 0))
        df['competition_index'] = df.groupby(['primary_theme', 'congress_number'])['bill_code'].transform('count')
        df['member_theme_focus'] = df['member_name'].map(compute_member_theme_focus(df))
        df['committee_overlap'] = compute_committee_overlap(df)
        df['chamber_lag_days'] = df['bill_status_str'].apply(get_chamber_lag)
        
        # Resolution URLs
        df['resolution_url'] = df.apply(
            lambda row: make_ldr_url(row['res_type'], row['res_number'], row['congress_number'])
            if pd.notna(row['res_type']) and pd.notna(row['res_number']) and pd.notna(row['congress_number'])
            else np.nan,
            axis=1
        )
    
        # Save processed file
        fp = f'{house}_bills_extended.csv'
        df.to_csv(fp, index=False)
        print("Saved: ", fp)

if __name__ == "__main__":
    main()