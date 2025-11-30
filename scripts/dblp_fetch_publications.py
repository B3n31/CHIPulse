import sqlite3
import time
from pathlib import Path
import requests
import xml.etree.ElementTree as ET

DB_PATH = Path("database/chi_ac.db")

BASE_SLEEP = 2       
MAX_RETRIES = 5

MIN_YEAR = 2005
MAX_YEAR = 2025


MAX_PERSONS_PER_RUN = 400

def fetch_author_xml(pid: str) -> str | None:

    url = f"https://dblp.org/pid/{pid}.xml"
    backoff = 5

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, timeout=20)
        except requests.RequestException as e:
            print(f"  Internet Erro({e}), Wait {backoff}s then retry")
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
            continue

        if resp.status_code == 429:
            print(f"  429 Too Many Requests, Wait {backoff}s then retry")
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
            continue

        if 500 <= resp.status_code < 600:
            print(f"  Server {resp.status_code}, Wait {backoff}s then retry")
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
            continue

        if not resp.ok:
            print(f"  HTTP {resp.status_code}, skip")
            return None

        return resp.text

    print("  Error multiple times, skip")
    return None

def parse_and_store_person_pubs(conn, person_id: int, pid: str, xml_text: str):
    cur = conn.cursor()
    root = ET.fromstring(xml_text)

    # dblpperson / r / <inproceedings|article|...>
    for r in root.findall("./r"):
        pub = None
        for child in r:
            pub = child
            break
        if pub is None:
            continue

        pub_type = pub.tag
        key = pub.get("key")
        if not key:
            continue

        # year
        year_el = pub.find("year")
        if year_el is None or not year_el.text:
            continue
        try:
            year = int(year_el.text.strip())
        except ValueError:
            continue

        if year < MIN_YEAR or year > MAX_YEAR:
            continue

        title_el = pub.find("title")
        title = title_el.text.strip() if title_el is not None and title_el.text else None

        venue_el = pub.find("booktitle")
        if venue_el is None or not venue_el.text:
            venue_el = pub.find("journal")
        venue = venue_el.text.strip() if venue_el is not None and venue_el.text else None

        doi = None
        ee = None
        for url_el in pub.findall("ee"):
            if url_el.text:
                ee = url_el.text.strip()
                if "doi.org" in ee or ee.startswith("10."):
                    doi = ee


        cur.execute("""
            INSERT OR IGNORE INTO publications (pub_key, title, year, venue, pub_type, doi, ee)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (key, title, year, venue, pub_type, doi, ee))

        # authorship
        cur.execute("""
            INSERT OR IGNORE INTO authorships (pub_key, person_id, author_pos)
            VALUES (?, ?, ?)
        """, (key, person_id, -1))

    conn.commit()

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT p.person_id, p.canonical_name, p.dblp_pid, 
               COUNT(a.pub_key) AS n_pubs
        FROM persons p
        LEFT JOIN authorships a
          ON p.person_id = a.person_id
        WHERE p.match_status IN ('matched_exact', 'matched_fuzzy')
        GROUP BY p.person_id
        HAVING n_pubs = 0
        ORDER BY p.person_id
    """)
    persons_missing = cur.fetchall()

    total_missing = len(persons_missing)
    print(f" {total_missing} AC no pub records")

    if total_missing == 0:
        conn.close()
        print("no need re-run")
        return

    persons_to_run = persons_missing[:MAX_PERSONS_PER_RUN]
    print(f" Got{len(persons_to_run)} AC with 2005–{MAX_YEAR}")

    for idx, (person_id, name, pid, n_pubs) in enumerate(persons_to_run, start=1):
        if not pid:
            continue

        print(f"[{idx}/{len(persons_to_run)}] {name} ({pid}) ...")
        xml_text = fetch_author_xml(pid)
        if not xml_text:
            continue

        try:
            parse_and_store_person_pubs(conn, person_id, pid, xml_text)
        except Exception as e:
            print(f"  Written Error: {e}")

        time.sleep(BASE_SLEEP)

    conn.close()
    print("Finished")

if __name__ == "__main__":
    main()
