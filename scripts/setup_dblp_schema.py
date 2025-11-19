import sqlite3
from pathlib import Path

DB_PATH = Path("database/chi_ac.db")  # 视你的目录调整

def column_exists(cur, table, col):
    cur.execute(f"PRAGMA table_info({table});")
    cols = [r[1] for r in cur.fetchall()]
    return col in cols

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # persons 表加 dblp_pid / dblp_url 列（如果还没有）
    if not column_exists(cur, "persons", "dblp_pid"):
        cur.execute("ALTER TABLE persons ADD COLUMN dblp_pid TEXT;")
    if not column_exists(cur, "persons", "dblp_url"):
        cur.execute("ALTER TABLE persons ADD COLUMN dblp_url TEXT;")

    # 建候选表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS person_dblp_candidates (
            candidate_id   INTEGER PRIMARY KEY,
            person_id      INTEGER NOT NULL,
            dblp_pid       TEXT NOT NULL,
            dblp_url       TEXT NOT NULL,
            author_name    TEXT NOT NULL,
            score          REAL,
            chosen         INTEGER DEFAULT 0,
            FOREIGN KEY(person_id) REFERENCES persons(person_id)
        );
    """)

    conn.commit()
    conn.close()
    print("DBLP 相关 schema 已准备好")

if __name__ == "__main__":
    main()
