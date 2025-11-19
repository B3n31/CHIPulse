import sqlite3
import unicodedata
import re
from pathlib import Path

DB_PATH = Path("database/chi_ac.db")

def name_tokens(s: str):
    # 去重音、转小写、去掉标点，只留字母和空格 → token list
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^a-z\s]", " ", s)
    toks = [t for t in s.split() if t]
    return toks

def name_similarity(canon: str, author: str) -> float:
    t1 = name_tokens(canon)
    t2 = name_tokens(author)
    if not t1 or not t2:
        return 0.0

    set1, set2 = set(t1), set(t2)
    inter = len(set1 & set2)
    union = len(set1 | set2)
    jacc = inter / union if union else 0.0

    # 姓氏 bonus
    last1, last2 = t1[-1], t2[-1]
    bonus = 0.2 if last1 == last2 else 0.0

    sim = min(1.0, jacc + bonus)

    # 完全同 token 视为 1.0
    if t1 == t2:
        sim = 1.0

    return sim

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT person_id, canonical_name FROM persons")
    persons = cur.fetchall()
    print(f"总共 {len(persons)} 人，开始匹配 DBLP pid...")

    for idx, (person_id, canon) in enumerate(persons, start=1):
        cur.execute("""
            SELECT candidate_id, dblp_pid, dblp_url, author_name
            FROM person_dblp_candidates
            WHERE person_id = ?
        """, (person_id,))
        cands = cur.fetchall()

        if not cands:
            cur.execute("""
                UPDATE persons
                SET match_status = 'no_candidate'
                WHERE person_id = ?
            """, (person_id,))
            continue

        sims = []
        for cand_id, pid, url, author in cands:
            sim = name_similarity(canon, author)
            sims.append((sim, cand_id, pid, url, author))

        sims.sort(reverse=True, key=lambda x: x[0])
        best_sim, best_cid, best_pid, best_url, best_name = sims[0]
        second_sim = sims[1][0] if len(sims) > 1 else 0.0

        # 规则：
        # 1. sim>=0.9 且明显领先 → matched_exact
        # 2. sim>=0.75 且领先 0.15 → matched_fuzzy
        # 否则 ambiguous
        if best_sim >= 0.9 and best_sim - second_sim >= 0.1:
            status = "matched_exact"
            choose = True
        elif best_sim >= 0.75 and best_sim - second_sim >= 0.15:
            status = "matched_fuzzy"
            choose = True
        else:
            status = "ambiguous"
            choose = False

        if choose:
            cur.execute("""
                UPDATE persons
                SET dblp_pid = ?, dblp_url = ?, match_status = ?
                WHERE person_id = ?
            """, (best_pid, best_url, status, person_id))

            cur.execute("""
                UPDATE person_dblp_candidates
                SET chosen = 1
                WHERE candidate_id = ?
            """, (best_cid,))
        else:
            cur.execute("""
                UPDATE persons
                SET match_status = ?
                WHERE person_id = ?
            """, (status, person_id))

        if idx % 100 == 0:
            conn.commit()
            print(f"已处理 {idx}/{len(persons)}")

    conn.commit()
    conn.close()
    print("v2 匹配完成。")

if __name__ == "__main__":
    main()
