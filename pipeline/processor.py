"""
processor.py
-------------
Downloader ne jo raw JSON files data/raw/ mein daali hain, unhe uthata hai,
clean karta hai, aur MySQL mein raw SQL se insert karta hai.

Design: latest raw file uthata hai by default (tu chahe toh sabhi files bhi
process kar sakta hai loop lagakar - demo ke liye latest kaafi hai).
"""

import json
import os
import glob
import mysql.connector
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from config import DB_CONFIG

RAW_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
PROCESSED_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")


def get_latest_raw_file():
    """data/raw/ mein sabse naya JSON file dhoondta hai (filename mein timestamp hai isliye sort easy hai)."""
    files = glob.glob(os.path.join(RAW_DATA_DIR, "raw_*.json"))
    if not files:
        raise FileNotFoundError("Koi raw file nahi mili. Pehle downloader.py chala.")
    latest = max(files, key=os.path.getctime)
    return latest


def clean_document(raw_doc: dict) -> dict:
    """
    Ek raw document object leta hai aur DB-ready dictionary banata hai.
    - agencies: list of dicts hoti hai API se, hum sirf naam nikal ke comma-joined string banate hain
    - missing fields ke liye None fallback rakha hai
    """
    agencies_list = raw_doc.get("agencies", [])
    agency_names = ", ".join([a.get("name", "") for a in agencies_list]) if agencies_list else None

    return {
        "document_number": raw_doc.get("document_number"),
        "title": raw_doc.get("title"),
        "abstract": raw_doc.get("abstract"),
        "publication_date": raw_doc.get("publication_date"),
        "agencies": agency_names,
        "doc_type": raw_doc.get("type"),
        "html_url": raw_doc.get("html_url"),
    }


def save_processed_copy(cleaned_docs: list):
    """Processed data ka bhi ek copy rakh lete hain disk pe - debugging aur record-keeping ke liye."""
    os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
    filepath = os.path.join(PROCESSED_DATA_DIR, "latest_processed.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(cleaned_docs, f, indent=2, ensure_ascii=False)
    print(f"Processed copy saved to: {filepath}")


def insert_into_mysql(cleaned_docs: list):
    """
    Raw SQL se insert karta hai. ON DUPLICATE KEY UPDATE isliye lagaya hai
    taaki agar wahi document dubara aaye (daily pipeline re-run hone par),
    toh error na aaye - bas update ho jaaye. Isse pipeline safely baar baar
    chalayi ja sakti hai (idempotent).
    """
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    insert_query = """
        INSERT INTO documents
            (document_number, title, abstract, publication_date, agencies, doc_type, html_url)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            title = VALUES(title),
            abstract = VALUES(abstract),
            agencies = VALUES(agencies)
    """

    rows_inserted = 0
    for doc in cleaned_docs:
        values = (
            doc["document_number"],
            doc["title"],
            doc["abstract"],
            doc["publication_date"],
            doc["agencies"],
            doc["doc_type"],
            doc["html_url"],
        )
        cursor.execute(insert_query, values)
        rows_inserted += 1

    conn.commit()  # yahan tak sab kuch DB mein permanently save ho jaata hai
    cursor.close()
    conn.close()
    print(f"{rows_inserted} documents inserted/updated in MySQL.")


if __name__ == "__main__":
    latest_file = get_latest_raw_file()
    print(f"Processing: {latest_file}")

    with open(latest_file, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    raw_docs = raw_data.get("results", [])
    cleaned_docs = [clean_document(d) for d in raw_docs]

    save_processed_copy(cleaned_docs)
    insert_into_mysql(cleaned_docs)
