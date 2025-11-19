import sqlite3
from pathlib import Path

DB_PATH = Path("database/chi_ac.db")

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 清空 persons 里的匹配结果
    cur.execute("""
        UPDATE persons
        SET dblp_pid = NULL,
            dblp_url = NULL,
            match_status = 'unmatched'
    """)

    # 清空候选表里的 chosen 标记
    cur.execute("""
        UPDATE person_dblp_candidates
        SET chosen = 0
    """)

    conn.commit()
    conn.close()
    print("已重置 dblp 匹配状态")

if __name__ == "__main__":
    main()
