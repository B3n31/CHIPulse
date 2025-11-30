import sqlite3
from pathlib import Path

DB_PATH = Path("database/chi_ac.db")

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        UPDATE persons
        SET dblp_pid = NULL,
            dblp_url = NULL,
            match_status = 'unmatched'
    """)

    cur.execute("""
        UPDATE person_dblp_candidates
        SET chosen = 0
    """)

    conn.commit()
    conn.close()
    print("Finish Reset")

if __name__ == "__main__":
    main()
