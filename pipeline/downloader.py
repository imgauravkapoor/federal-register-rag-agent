"""
downloader.py
--------------
Sirf ek kaam: Federal Register API se documents fetch karo, raw JSON save karo.
Koi cleaning, koi DB insert nahi - wo processor.py ka kaam hai.
"""

import requests
import json
import os
from datetime import datetime, timedelta

RAW_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
BASE_URL = "https://www.federalregister.gov/api/v1/documents.json"


def fetch_recent_documents(days_back: int = 60, per_page: int = 100):
    """
    Pichle `days_back` dinon ke documents fetch karta hai.
    JD allows 'past 2 month data' - isliye default 60 din rakha hai.
    """
    end_date = datetime.today().date()
    start_date = end_date - timedelta(days=days_back)

    params = {
        "conditions[publication_date][gte]": start_date.isoformat(),
        "conditions[publication_date][lte]": end_date.isoformat(),
        "per_page": per_page,
        "order": "newest",
        # sirf wahi fields lo jo humein chahiye - response halka rahega
        "fields[]": [
            "document_number",
            "title",
            "abstract",
            "publication_date",
            "agencies",
            "type",
            "html_url",
        ],
    }

    print(f"Fetching documents from {start_date} to {end_date}...")
    response = requests.get(BASE_URL, params=params, timeout=30)
    response.raise_for_status()  # agar API fail ho toh yahin error throw ho jaayega

    data = response.json()
    print(f"Fetched {len(data.get('results', []))} documents (total available: {data.get('count')})")
    return data


def save_raw_data(data: dict):
    """
    Raw response ko as-is save karta hai, filename mein aaj ki date + timestamp -
    isse hum har pipeline run ka record rakh paate hain (JD requirement: 1 week records).
    """
    os.makedirs(RAW_DATA_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filepath = os.path.join(RAW_DATA_DIR, f"raw_{timestamp}.json")

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Raw data saved to: {filepath}")
    return filepath


if __name__ == "__main__":
    raw = fetch_recent_documents(days_back=60)
    save_raw_data(raw)
