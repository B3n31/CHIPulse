import sqlite3
from pathlib import Path
import requests
import time
import unicodedata

DB_PATH = Path("database/chi_ac.db")
DBLP_SEARCH_URL = "https://dblp.org/search/author/api"

MAX_SUCCESS_PER_RUN = 500

# Base sleep time (seconds) between each request
BASE_SLEEP = 8

def normalize_name(s: str) -> str:
    """Remove accents + lowercase; used for simple scoring."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower().strip()

def search_dblp(name: str, max_retries: int = 6):
    """
    DBLP search with retry + exponential backoff:
    - 429 / 5xx / network errors → retry with backoff
    - Success → return list of hits
    - After repeated failures → return []
    """
    params = {"q": name, "format": "json"}
    backoff = 10  # initial backoff (seconds), doubling up to 40

    for attempt in range(max_retries):
        try:
            resp = requests.get(DBLP_SEARCH_URL, params=params, timeout=20)
        except requests.RequestException as e:
            print(f"  Network error ({e}), retrying in {backoff}s...")
            time.sleep(backoff)
            backoff = min(backoff * 2, 40)
            continue

        # Rate limit
        if resp.status_code == 429:
            print(f"  429 Too Many Requests, retrying in {backoff}s...")
            time.sleep(backoff)
            backoff = min(backoff * 2, 40)
            continue

        # Server-side error
        if 500 <= resp.status_code < 600:
            print(f"  Server error {resp.status_code}, retrying in {backoff}s...")
            time.sleep(backoff)
            backoff = min(backoff * 2, 40)
            continue

        try:
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"  Other HTTP error ({e}), skipping this person")
            return []

        data = resp.json()
        hits = data.get("result", {}).get("hits", {}).get("hit", [])
        if isinstance(hits, dict):
            hits = [hits]
        return hits

    print("  Failed after repeated retries, skipping this person")
    return []

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Resume support: only process persons not yet in person_dblp_candidates
    cur.execute("""
        SELECT person_id, canonical_name
        FROM persons
        WHERE person_id NOT IN (
            SELECT DISTINCT person_id FROM person_dblp_candidates
        )
        ORDER BY person_id
    """)
    persons = cur.fetchall()
    total = len(persons)
    print(f"{total} names need DBLP search")

    success = 0 

    for idx, (person_id, name) in enumerate(persons, start=1):
        if success >= MAX_SUCCESS_PER_RUN:
            print(f"Reached {success} successful persons for this run, stopping for now.")
            break

        print(f"[{idx}/{total}] Searching {name} ...")

        hits = search_dblp(name)
        base = normalize_name(name)

        inserted = 0
        for h in hits:
            info = h.get("info", {})
            author_name = info.get("author")
            url = info.get("url")
            if not author_name or not url:
                continue

            # URL like: https://dblp.org/pid/12/1234 → pid = "12/1234"
            pid = url.split("pid/")[-1]

            score = 1.0 if normalize_name(author_name) == base else 0.0

            cur.execute("""
                INSERT INTO person_dblp_candidates
                    (person_id, dblp_pid, dblp_url, author_name, score)
                VALUES (?, ?, ?, ?, ?)
            """, (person_id, pid, url, author_name, score))
            inserted += 1

        conn.commit()

        if inserted > 0:
            success += 1

        # Base pacing: always sleep a bit after each person
        time.sleep(BASE_SLEEP)

    conn.close()
    print(f"DBLP search finished, successfully processed {success} persons in this run")

if __name__ == "__main__":
    main()
