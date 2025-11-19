import csv
import sqlite3
from pathlib import Path

DB_PATH = Path("database/chi_ac.db")
CSV_PATH = Path("data/raw/committee_members_cleaned.csv")

def parse_member(member: str):
    """
    支持两种格式：
    1) 'Ravin Balakrishnan, University of Toronto, Canada'
    2) 'James Fogarty (University of Washington)'
       'Bill Gaver (Goldsmiths College, University of London)'
    返回: name, affiliation, country
    """
    member = member.strip().strip('"')

    # --- 先处理括号格式: Name (Affiliation[, Country]) ---
    # 例如: 'James Fogarty (University of Washington)'
    if "(" in member and member.endswith(")"):
        name_part, rest = member.split("(", 1)
        name = name_part.strip()
        inside = rest[:-1].strip()  # 去掉最后一个 ')'

        # 括号内再按逗号拆 affiliation / country
        inside_parts = [p.strip() for p in inside.split(",") if p.strip()]
        if len(inside_parts) == 0:
            return name, None, None
        elif len(inside_parts) == 1:
            # 只有机构，没有国家
            return name, inside_parts[0], None
        else:
            # 最后一段当国家，其余合成机构
            affiliation = ", ".join(inside_parts[:-1])
            country = inside_parts[-1]
            return name, affiliation, country

    # --- 否则走逗号格式: Name, Affiliation[, Country] ---
    parts = [p.strip() for p in member.split(",") if p.strip()]
    if not parts:
        return None, None, None

    name = parts[0]

    if len(parts) == 1:
        # 只有名字
        return name, None, None
    elif len(parts) == 2:
        # 名字 + 机构
        return name, parts[1], None
    else:
        # 名字 + 机构..., 国家
        affiliation = ", ".join(parts[1:-1])
        country = parts[-1]
        return name, affiliation, country


def create_tables(conn):
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS ac_roles;")
    cur.execute("DROP TABLE IF EXISTS persons;")

    # 人表（只放名字，后面再加 dblp_pid 等）
    cur.execute("""
        CREATE TABLE persons (
            person_id      INTEGER PRIMARY KEY,
            canonical_name TEXT NOT NULL,
            match_status   TEXT NOT NULL DEFAULT 'unmatched'
        );
    """)

    # AC 记录表：年份 + 场地 + 原始字符串 + 拆出来的字段
    cur.execute("""
        CREATE TABLE ac_roles (
            ac_role_id      INTEGER PRIMARY KEY,
            year            INTEGER NOT NULL,
            venue           TEXT NOT NULL,
            committee       TEXT NOT NULL,
            member_raw      TEXT NOT NULL,
            name_clean      TEXT NOT NULL,
            affiliation_raw TEXT,
            country         TEXT,
            person_id       INTEGER,
            FOREIGN KEY(person_id) REFERENCES persons(person_id)
        );
    """)

    conn.commit()

def import_ac_roles(conn):
    cur = conn.cursor()
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)   # 要求第一行是 year,venue,committee,member
        for row in reader:
            member = row["member"]
            name_clean, affiliation_raw, country = parse_member(member)

            cur.execute("""
                INSERT INTO ac_roles
                    (year, venue, committee, member_raw,
                     name_clean, affiliation_raw, country)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                int(row["year"]),
                row["venue"],
                row["committee"],
                member,
                name_clean,
                affiliation_raw,
                country
            ))
    conn.commit()

def build_persons_and_link(conn):
    cur = conn.cursor()

    # 生成 persons（按姓名去重）
    cur.execute("""
        INSERT INTO persons (canonical_name)
        SELECT DISTINCT name_clean
        FROM ac_roles;
    """)

    # 把 person_id 回填到 ac_roles
    cur.execute("""
        UPDATE ac_roles
        SET person_id = (
            SELECT person_id
            FROM persons
            WHERE persons.canonical_name = ac_roles.name_clean
        );
    """)

    conn.commit()

def main():
    conn = sqlite3.connect(DB_PATH)
    create_tables(conn)
    import_ac_roles(conn)
    build_persons_and_link(conn)
    conn.close()
    print("OK, 写到 chi_ac.db 里了")

if __name__ == "__main__":
    main()
