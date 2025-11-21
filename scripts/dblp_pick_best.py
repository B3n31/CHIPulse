import sqlite3
import unicodedata
import re
from pathlib import Path

DB_PATH = Path("database/chi_ac.db")

def name_tokens(s: str):
    """
    去重音、转小写、去掉标点，只留字母和空格 → token list
    """
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^a-z\s]", " ", s)
    toks = [t for t in s.split() if t]
    return toks

def name_key(s: str) -> str:
    """
    规范化名字，用于“强一致”匹配：
    Xing-Dong Yang / Xing dong Yang / xing-dong yang -> "xing dong yang"
    """
    return " ".join(name_tokens(s))

def name_similarity(canon: str, author: str) -> float:
    """
    简单名字相似度：
    - token Jaccard
    - 姓氏相同 +0.2
    - 完全同 token 直接 1.0
    """
    t1 = name_tokens(canon)
    t2 = name_tokens(author)
    if not t1 or not t2:
        return 0.0

    set1, set2 = set(t1), set(t2)
    inter = len(set1 & set2)
    union = len(set1 | set2)
    jacc = inter / union if union else 0.0

    last1, last2 = t1[-1], t2[-1]
    bonus = 0.2 if last1 == last2 else 0.0

    sim = min(1.0, jacc + bonus)

    if t1 == t2:
        sim = 1.0

    return sim

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 确保列存在
    cur.execute("PRAGMA table_info(persons);")
    cols = {row[1] for row in cur.fetchall()}
    if "dblp_pid" not in cols:
        cur.execute("ALTER TABLE persons ADD COLUMN dblp_pid TEXT;")
    if "dblp_url" not in cols:
        cur.execute("ALTER TABLE persons ADD COLUMN dblp_url TEXT;")
    if "match_status" not in cols:
        cur.execute("ALTER TABLE persons ADD COLUMN match_status TEXT NOT NULL DEFAULT 'unknown';")
    conn.commit()

    # 清空旧结果
    cur.execute("UPDATE person_dblp_candidates SET chosen = 0;")
    cur.execute("""
        UPDATE persons
        SET dblp_pid = NULL,
            dblp_url = NULL,
            match_status = 'unknown';
    """)
    conn.commit()

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

        canon_k = name_key(canon)

        # 1️⃣ 先找“规范化名字完全一致”的候选
        exact_key_cands = []
        sims = []

        for cand_id, pid, url, author in cands:
            ak = name_key(author)
            sim = name_similarity(canon, author)
            sims.append((sim, cand_id, pid, url, author, ak))
            if ak == canon_k:
                exact_key_cands.append((sim, cand_id, pid, url, author, ak))

        if exact_key_cands:
            # 有至少一个 key 完全一致的，直接挑相似度最高的那个
            exact_key_cands.sort(reverse=True, key=lambda x: x[0])
            best_sim, best_cid, best_pid, best_url, best_name, _ = exact_key_cands[0]
            status = "matched_exact"
            choose = True
        else:
            # 2️⃣ 否则退回原来的 best_sim / second_sim 逻辑
            sims.sort(reverse=True, key=lambda x: x[0])
            best_sim, best_cid, best_pid, best_url, best_name, _ = sims[0]
            second_sim = sims[1][0] if len(sims) > 1 else 0.0
            cand_count = len(sims)

            status = "ambiguous"
            choose = False

            if cand_count == 1:
                if best_sim >= 0.80:
                    status = "matched_fuzzy"
                    choose = True
                elif best_sim >= 0.70:
                    status = "matched_loose"
                    choose = True
            else:
                diff = best_sim - second_sim
                if best_sim >= 0.90 and diff >= 0.05:
                    status = "matched_exact"
                    choose = True
                elif best_sim >= 0.80 and diff >= 0.10:
                    status = "matched_fuzzy"
                    choose = True

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
    print("v2-key 匹配完成。")

if __name__ == "__main__":
    main()
