import sqlite3
from pathlib import Path

DB_PATH = Path("database/chi_ac.db")

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("=== 每个 person 的候选数量分布（前 20） ===")
    cur.execute("""
        SELECT person_id, COUNT(*) AS cnt
        FROM person_dblp_candidates
        GROUP BY person_id
        ORDER BY cnt DESC
        LIMIT 20;
    """)
    for person_id, cnt in cur.fetchall():
        print(person_id, cnt)

    print("\n=== 各种 match_status 计数（如果已经跑过 pick_best） ===")
    cur.execute("""
        SELECT match_status, COUNT(*)
        FROM persons
        GROUP BY match_status;
    """)
    for status, n in cur.fetchall():
        print(status, n)

    conn.close()

if __name__ == "__main__":
    main()
