import sqlite3
from pathlib import Path
import requests
import time
import unicodedata

DB_PATH = Path("database/chi_ac.db")
DBLP_SEARCH_URL = "https://dblp.org/search/author/api"

# 每次运行最多成功处理多少个 person，避免一口气打完 2600 个
MAX_SUCCESS_PER_RUN = 2000

# 正常情况下，两次请求之间的固定间隔（秒）
BASE_SLEEP = 8

def normalize_name(s: str) -> str:
    """去重音 + 小写，用来简单算 score"""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower().strip()

def search_dblp(name: str, max_retries: int = 6):
    """
    带退避重试的 DBLP 搜索：
    - 429 / 5xx / 网络错误：指数退避
    - 成功：返回 hits 列表
    - 多次失败：返回 []
    """
    params = {"q": name, "format": "json"}
    backoff = 10  # 起始退避 10 秒，后面翻倍，最多到 40

    for attempt in range(max_retries):
        try:
            resp = requests.get(DBLP_SEARCH_URL, params=params, timeout=20)
        except requests.RequestException as e:
            print(f"  网络错误({e}), 等 {backoff}s 重试...")
            time.sleep(backoff)
            backoff = min(backoff * 2, 40)
            continue

        # 限流
        if resp.status_code == 429:
            print(f"  429 Too Many Requests, 等 {backoff}s 再试...")
            time.sleep(backoff)
            backoff = min(backoff * 2, 40)
            continue

        # 服务器 5xx
        if 500 <= resp.status_code < 600:
            print(f"  服务器错误 {resp.status_code}, 等 {backoff}s 再试...")
            time.sleep(backoff)
            backoff = min(backoff * 2, 40)
            continue

        try:
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"  其他 HTTP 错误({e})，不再重试，跳过这个人")
            return []

        data = resp.json()
        hits = data.get("result", {}).get("hits", {}).get("hit", [])
        if isinstance(hits, dict):
            hits = [hits]
        return hits

    print("  多次重试仍失败，先跳过这个人")
    return []

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # ✅ 断点续跑：只选还没在 person_dblp_candidates 出现过的人
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
    print(f"需要搜索 {total} 个名字")

    success = 0  # 本轮已经成功处理多少 person

    for idx, (person_id, name) in enumerate(persons, start=1):
        if success >= MAX_SUCCESS_PER_RUN:
            print(f"本轮已成功处理 {success} 个，先停在这里，下次再继续。")
            break

        print(f"[{idx}/{total}] 搜索 {name} ...")

        hits = search_dblp(name)
        base = normalize_name(name)

        inserted = 0
        for h in hits:
            info = h.get("info", {})
            author_name = info.get("author")
            url = info.get("url")
            if not author_name or not url:
                continue

            # url 形如 'https://dblp.org/pid/37/1234' → pid '37/1234'
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

        # 基础节奏：无论有没有 429，每搜完一个人都慢一点
        time.sleep(BASE_SLEEP)

    conn.close()
    print(f"DBLP 搜索完成，本轮成功处理 {success} 个")

if __name__ == "__main__":
    main()
