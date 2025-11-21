import sqlite3
from pathlib import Path

DB_PATH = Path("database/chi_ac.db")

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 论文表：一篇 paper 一行
    cur.execute("""
        CREATE TABLE IF NOT EXISTS publications (
            pub_key   TEXT PRIMARY KEY,      -- dblp 的 key，例如 conf/chi/2005/xxx
            title     TEXT,
            year      INTEGER,
            venue     TEXT,                  -- conference/journal 名
            pub_type  TEXT,                  -- inproceedings/article/... 
            doi       TEXT,
            ee        TEXT                   -- external electronic edition
        );
    """)

    # authorship：哪位 AC 参与了哪篇 paper
    cur.execute("""
        CREATE TABLE IF NOT EXISTS authorships (
            pub_key    TEXT,
            person_id  INTEGER,
            author_pos INTEGER,              -- 在 author 列表里的位置
            PRIMARY KEY (pub_key, person_id),
            FOREIGN KEY (pub_key)  REFERENCES publications(pub_key),
            FOREIGN KEY (person_id) REFERENCES persons(person_id)
        );
    """)

    conn.commit()
    conn.close()
    print("tables created.")

if __name__ == "__main__":
    main()
