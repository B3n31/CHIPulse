import sqlite3
import time
from pathlib import Path
import requests
import xml.etree.ElementTree as ET

DB_PATH = Path("database/chi_ac.db")

BASE_SLEEP = 2         # 每个 author 之间的基础间隔
MAX_RETRIES = 5

MIN_YEAR = 2005
MAX_YEAR = 2025

# 每轮最多爬多少个人，防止一下子打太多（可以调大调小）
MAX_PERSONS_PER_RUN = 400

def fetch_author_xml(pid: str) -> str | None:
    """
    从 DBLP 拉某个 author 的 XML：
    https://dblp.org/pid/<pid>.xml
    带简单重试 + 429/backoff
    """
    url = f"https://dblp.org/pid/{pid}.xml"
    backoff = 5

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, timeout=20)
        except requests.RequestException as e:
            print(f"  网络错误({e}), 等 {backoff}s 重试...")
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
            continue

        if resp.status_code == 429:
            print(f"  429 Too Many Requests, 等 {backoff}s 重试...")
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
            continue

        if 500 <= resp.status_code < 600:
            print(f"  服务器错误 {resp.status_code}, 等 {backoff}s 重试...")
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
            continue

        if not resp.ok:
            print(f"  HTTP {resp.status_code}, 跳过这个人")
            return None

        return resp.text

    print("  多次重试仍失败，跳过这个人")
    return None

def parse_and_store_person_pubs(conn, person_id: int, pid: str, xml_text: str):
    """
    解析 dblpperson XML，把 2005–2025 年的论文写入 DB
    """
    cur = conn.cursor()
    root = ET.fromstring(xml_text)

    # dblpperson / r / <inproceedings|article|...>
    for r in root.findall("./r"):
        # r 下面一般只有一个 publication 节点
        pub = None
        for child in r:
            pub = child
            break
        if pub is None:
            continue

        pub_type = pub.tag  # article / inproceedings / incollection / ...
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

        # 只保留 2005–2025
        if year < MIN_YEAR or year > MAX_YEAR:
            continue

        # title
        title_el = pub.find("title")
        title = title_el.text.strip() if title_el is not None and title_el.text else None

        # venue：conference 用 booktitle，journal 用 journal
        venue_el = pub.find("booktitle")
        if venue_el is None or not venue_el.text:
            venue_el = pub.find("journal")
        venue = venue_el.text.strip() if venue_el is not None and venue_el.text else None

        # doi / ee
        doi = None
        ee = None
        for url_el in pub.findall("ee"):
            if url_el.text:
                ee = url_el.text.strip()
                if "doi.org" in ee or ee.startswith("10."):
                    doi = ee

        # 写 publications：用 key 做主键，避免同一篇被多个 AC 重复插入
        cur.execute("""
            INSERT OR IGNORE INTO publications (pub_key, title, year, venue, pub_type, doi, ee)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (key, title, year, venue, pub_type, doi, ee))

        # authorship：简单记“这个 AC 参与了这篇 paper”
        cur.execute("""
            INSERT OR IGNORE INTO authorships (pub_key, person_id, author_pos)
            VALUES (?, ?, ?)
        """, (key, person_id, -1))

    conn.commit()

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 先看：high-conf 里哪些人“还没有任何 authorship 记录”
    # 注意：authorships 现在只存 2005–2025 的 paper，所以只要没有记录就说明没爬过
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
    print(f"还有 {total_missing} 位 AC 在数据库里还没有任何论文记录")

    if total_missing == 0:
        conn.close()
        print("没有需要补爬的人，直接结束。")
        return

    # 本轮只跑前 MAX_PERSONS_PER_RUN 个，避免一次性打太多请求
    persons_to_run = persons_missing[:MAX_PERSONS_PER_RUN]
    print(f"本轮准备为其中 {len(persons_to_run)} 位 AC 抓取 2005–{MAX_YEAR} 的论文")

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
            print(f"  解析/写入出错: {e}")

        time.sleep(BASE_SLEEP)

    conn.close()
    print("本轮抓取完成。")

if __name__ == "__main__":
    main()
