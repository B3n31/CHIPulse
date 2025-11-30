# scripts/db_queries.py
import json
from typing import List, Dict, Any, Optional
from db_utils import run_sql

# ======================
# 1. Yearly / Affiliation Statistics
# ======================

def get_ac_year_stats_all() -> List[Dict[str, Any]]:
    """
    Yearly total number of ACs (all persons, regardless of DBLP matching).
    Returns: [{year, ac_count}, ...]
    """
    rows = run_sql(
        """
        SELECT
            year AS year,
            COUNT(DISTINCT person_id) AS ac_count
        FROM ac_roles
        GROUP BY year
        ORDER BY year
        """
    )
    return [{"year": r["year"], "ac_count": r["ac_count"]} for r in rows]


def get_ac_year_stats_high_conf() -> List[Dict[str, Any]]:
    """
    Yearly number of ACs in persons_high_conf (high-confidence DBLP matches).
    Returns: [{year, ac_count_high_conf}, ...]
    """
    rows = run_sql(
        """
        SELECT
            ar.year AS year,
            COUNT(DISTINCT ar.person_id) AS ac_count_high_conf
        FROM ac_roles ar
        JOIN persons_high_conf phc
          ON phc.person_id = ar.person_id
        GROUP BY ar.year
        ORDER BY ar.year
        """
    )
    return [
        {"year": r["year"], "ac_count_high_conf": r["ac_count_high_conf"]}
        for r in rows
    ]


def get_top_affiliations_high_conf(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Counts high-confidence AC appearances by affiliation (ac_roles.affiliation_raw).
    Each “person-year-committee” record counts as 1.
    Returns: [{affiliation, ac_roles_count}, ...]
    """
    rows = run_sql(
        """
        SELECT
            ar.affiliation_raw AS affiliation,
            COUNT(*) AS ac_roles_count
        FROM ac_roles ar
        JOIN persons_high_conf phc
          ON phc.person_id = ar.person_id
        WHERE ar.affiliation_raw IS NOT NULL
          AND ar.affiliation_raw != ''
        GROUP BY ar.affiliation_raw
        ORDER BY ac_roles_count DESC
        LIMIT ?
        """,
        (limit,),
    )
    return [
        {"affiliation": r["affiliation"], "ac_roles_count": r["ac_roles_count"]}
        for r in rows
    ]


def get_ac_list_by_year(
    year: int,
    high_conf_only: bool = False,
) -> List[Dict[str, Any]]:
    """
    AC list for a given year (optional: only high-confidence persons).
    Returns: [{person_id, name, year, venue, committee, affiliation, country}, ...]
    """
    if high_conf_only:
        rows = run_sql(
            """
            SELECT
                ar.person_id,
                p.canonical_name AS name,
                ar.year,
                ar.venue,
                ar.committee,
                ar.affiliation_raw AS affiliation,
                ar.country
            FROM ac_roles ar
            JOIN persons_high_conf phc
              ON phc.person_id = ar.person_id
            LEFT JOIN persons p
              ON p.person_id = ar.person_id
            WHERE ar.year = ?
            ORDER BY ar.venue, ar.committee, name
            """,
            (year,),
        )
    else:
        rows = run_sql(
            """
            SELECT
                ar.person_id,
                p.canonical_name AS name,
                ar.year,
                ar.venue,
                ar.committee,
                ar.affiliation_raw AS affiliation,
                ar.country
            FROM ac_roles ar
            LEFT JOIN persons p
              ON p.person_id = ar.person_id
            WHERE ar.year = ?
            ORDER BY ar.venue, ar.committee, name
            """,
            (year,),
        )
    return [dict(r) for r in rows]


def get_affiliation_trend(
    keyword: str,
    high_conf_only: bool = True,
) -> List[Dict[str, Any]]:
    """
    Query yearly trend for an institution (fuzzy keyword match).
    Example keywords: 'microsoft', 'toronto', 'google'
    Returns: [{year, ac_count}, ...]
    """
    pattern = f"%{keyword.lower()}%"
    if high_conf_only:
        rows = run_sql(
            """
            SELECT
                ar.year AS year,
                COUNT(DISTINCT ar.person_id) AS ac_count
            FROM ac_roles ar
            JOIN persons_high_conf phc
              ON phc.person_id = ar.person_id
            WHERE ar.affiliation_raw IS NOT NULL
              AND LOWER(ar.affiliation_raw) LIKE ?
            GROUP BY ar.year
            ORDER BY ar.year
            """,
            (pattern,),
        )
    else:
        rows = run_sql(
            """
            SELECT
                ar.year AS year,
                COUNT(DISTINCT ar.person_id) AS ac_count
            FROM ac_roles ar
            WHERE ar.affiliation_raw IS NOT NULL
              AND LOWER(ar.affiliation_raw) LIKE ?
            GROUP BY ar.year
            ORDER BY ar.year
            """,
            (pattern,),
        )
    return [{"year": r["year"], "ac_count": r["ac_count"]} for r in rows]


# ======================
# 2. Person Lookup / Profile
# ======================

def get_person_full_profile(person_id: int) -> Optional[Dict[str, Any]]:
    """
    For a given person_id, return:
    - Record from persons table
    - All AC roles across the years
    - All publications (from publications/authorships)
    """
    # Person basic info
    person_rows = run_sql(
        """
        SELECT *
        FROM persons
        WHERE person_id = ?
        """,
        (person_id,),
    )
    if not person_rows:
        return None
    person = dict(person_rows[0])

    # AC roles
    roles = run_sql(
        """
        SELECT year, venue, committee, affiliation_raw, country
        FROM ac_roles
        WHERE person_id = ?
        ORDER BY year, venue, committee
        """,
        (person_id,),
    )
    person["ac_roles"] = [dict(r) for r in roles]

    # Publications
    pubs = run_sql(
        """
        SELECT
            pub.pub_key,
            pub.title,
            pub.year,
            pub.venue,
            pub.pub_type,
            pub.doi,
            pub.ee,
            a.author_pos
        FROM authorships a
        JOIN publications pub
          ON pub.pub_key = a.pub_key
        WHERE a.person_id = ?
        ORDER BY pub.year, pub.venue
        """,
        (person_id,),
    )
    person["publications"] = [dict(p) for p in pubs]

    return person


def find_persons_by_name(
    name_substring: str,
    high_conf_only: bool = False,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Fuzzy search over persons by name substring.
    Useful when browsing in notebook.
    Returns: [{person_id, canonical_name, match_status, dblp_pid}, ...]
    """
    pattern = f"%{name_substring.lower()}%"
    if high_conf_only:
        rows = run_sql(
            """
            SELECT
                p.person_id,
                p.canonical_name,
                p.match_status,
                p.dblp_pid
            FROM persons p
            JOIN persons_high_conf phc
              ON phc.person_id = p.person_id
            WHERE LOWER(p.canonical_name) LIKE ?
            ORDER BY p.canonical_name
            LIMIT ?
            """,
            (pattern, limit),
        )
    else:
        rows = run_sql(
            """
            SELECT
                p.person_id,
                p.canonical_name,
                p.match_status,
                p.dblp_pid
            FROM persons p
            WHERE LOWER(p.canonical_name) LIKE ?
            ORDER BY p.canonical_name
            LIMIT ?
            """,
            (pattern, limit),
        )
    return [dict(r) for r in rows]


# ======================
# 3. Publications / Coauthor Structure
# ======================

def get_hci_ac_publication_stats() -> List[Dict[str, Any]]:
    """
    Distribution of publications authored by high-confidence ACs
    across years and venues.
    Returns: [{year, venue, paper_count, unique_ac_authors}, ...]
    """
    rows = run_sql(
        """
        SELECT
            pub.year AS year,
            pub.venue AS venue,
            COUNT(DISTINCT pub.pub_key) AS paper_count,
            COUNT(DISTINCT a.person_id) AS unique_ac_authors
        FROM authorships a
        JOIN persons_high_conf phc
          ON phc.person_id = a.person_id
        JOIN publications pub
          ON pub.pub_key = a.pub_key
        GROUP BY pub.year, pub.venue
        ORDER BY pub.year, pub.venue
        """
    )
    return [dict(r) for r in rows]


def get_person_pub_venues(person_id: int) -> List[Dict[str, Any]]:
    """
    Publication venues for a given AC.
    Returns: [{venue, paper_count, first_year, last_year}, ...]
    """
    rows = run_sql(
        """
        SELECT
            pub.venue AS venue,
            COUNT(*) AS paper_count,
            MIN(pub.year) AS first_year,
            MAX(pub.year) AS last_year
        FROM authorships a
        JOIN publications pub
          ON pub.pub_key = a.pub_key
        WHERE a.person_id = ?
        GROUP BY pub.venue
        ORDER BY paper_count DESC, venue
        """,
        (person_id,),
    )
    return [dict(r) for r in rows]


def get_coauthors_for_person(
    person_id: int,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Coauthor list for a given AC (from authorships table).
    Returns: [{coauthor_person_id, coauthor_name, paper_count}, ...]
    """
    rows = run_sql(
        """
        SELECT
            b.person_id AS coauthor_person_id,
            p2.canonical_name AS coauthor_name,
            COUNT(DISTINCT b.pub_key) AS paper_count
        FROM authorships a
        JOIN authorships b
          ON a.pub_key = b.pub_key
         AND a.person_id = ?
         AND b.person_id != ?
        LEFT JOIN persons p2
          ON p2.person_id = b.person_id
        GROUP BY b.person_id, p2.canonical_name
        ORDER BY paper_count DESC, coauthor_name
        LIMIT ?
        """,
        (person_id, person_id, limit),
    )
    return [dict(r) for r in rows]


def smart_person_lookup(name: str):
    """
    High-level wrapper:
    1) Fuzzy search by name
    2) Pick best match (first for now)
    3) Fetch full profile
    4) Fetch venue-level publication stats

    Returns:
    {
        "person": {...},
        "publications": [...]
    }
    """
    persons = find_persons_by_name(name_substring=name)

    if not persons or len(persons) == 0:
        return {"error": "no_match", "results": []}

    p = persons[0]
    pid = p["person_id"]

    profile = get_person_full_profile(person_id=pid)
    pubs = get_person_pub_venues(person_id=pid)

    return {
        "person": profile,
        "publications": pubs
    }


# ======================
# 4. Trend / Overview Utilities
# ======================

def get_top_countries_overall(
    limit: int = 20,
    high_conf_only: bool = True,
) -> List[Dict[str, Any]]:
    """
    Global distribution of ACs by country (counting unique persons).
    Returns: [{country, ac_count}, ...], sorted by ac_count desc.
    """
    if high_conf_only:
        rows = run_sql(
            """
            SELECT
                COALESCE(NULLIF(TRIM(ar.country), ''), 'Unknown') AS country,
                COUNT(DISTINCT ar.person_id) AS ac_count
            FROM ac_roles ar
            JOIN persons_high_conf phc
              ON phc.person_id = ar.person_id
            GROUP BY country
            ORDER BY ac_count DESC
            LIMIT ?
            """,
            (limit,),
        )
    else:
        rows = run_sql(
            """
            SELECT
                COALESCE(NULLIF(TRIM(country), ''), 'Unknown') AS country,
                COUNT(DISTINCT person_id) AS ac_count
            FROM ac_roles
            GROUP BY country
            ORDER BY ac_count DESC
            LIMIT ?
            """,
            (limit,),
        )

    return [
        {"country": r["country"], "ac_count": r["ac_count"]}
        for r in rows
    ]


def get_ac_year_overview(
    year: int,
    high_conf_only: bool = True,
    max_countries: int = 30,
    max_committees: int = 30,
) -> Dict[str, Any]:
    """
    Year-specific overview:
    - Total AC count
    - Country distribution with percentages
    - Committee distribution with percentages
    """
    # Total AC count
    if high_conf_only:
        total_rows = run_sql(
            """
            SELECT COUNT(DISTINCT ar.person_id) AS total_ac
            FROM ac_roles ar
            JOIN persons_high_conf phc
              ON phc.person_id = ar.person_id
            WHERE ar.year = ?
            """,
            (year,),
        )
    else:
        total_rows = run_sql(
            """
            SELECT COUNT(DISTINCT person_id) AS total_ac
            FROM ac_roles
            WHERE year = ?
            """,
            (year,),
        )

    total_ac = total_rows[0]["total_ac"] if total_rows else 0

    # Helper for adding percentages
    def add_percentage(rows, key_name: str, max_items: int):
        if total_ac <= 0:
            return []
        out = []
        for r in rows[:max_items]:
            cnt = r["ac_count"]
            out.append(
                {
                    key_name: r[key_name],
                    "ac_count": cnt,
                    "percentage": round(100.0 * cnt / total_ac, 2),
                }
            )
        return out

    # Country distribution
    if high_conf_only:
        country_rows = run_sql(
            """
            SELECT
                COALESCE(NULLIF(TRIM(ar.country), ''), 'Unknown') AS country,
                COUNT(DISTINCT ar.person_id) AS ac_count
            FROM ac_roles ar
            JOIN persons_high_conf phc
              ON phc.person_id = ar.person_id
            WHERE ar.year = ?
            GROUP BY country
            ORDER BY ac_count DESC
            """,
            (year,),
        )
    else:
        country_rows = run_sql(
            """
            SELECT
                COALESCE(NULLIF(TRIM(country), ''), 'Unknown') AS country,
                COUNT(DISTINCT person_id) AS ac_count
            FROM ac_roles
            WHERE year = ?
            GROUP BY country
            ORDER BY ac_count DESC
            """,
            (year,),
        )

    countries = add_percentage(country_rows, "country", max_countries)

    # Committee distribution
    if high_conf_only:
        committee_rows = run_sql(
            """
            SELECT
                COALESCE(NULLIF(TRIM(ar.committee), ''), 'Unknown') AS committee,
                COUNT(DISTINCT ar.person_id) AS ac_count
            FROM ac_roles ar
            JOIN persons_high_conf phc
              ON phc.person_id = ar.person_id
            WHERE ar.year = ?
            GROUP BY committee
            ORDER BY ac_count DESC
            """,
            (year,),
        )
    else:
        committee_rows = run_sql(
            """
            SELECT
                COALESCE(NULLIF(TRIM(committee), ''), 'Unknown') AS committee,
                COUNT(DISTINCT person_id) AS ac_count
            FROM ac_roles
            WHERE year = ?
            GROUP BY committee
            ORDER BY ac_count DESC
            """,
            (year,),
        )

    committees = add_percentage(committee_rows, "committee", max_committees)

    return {
        "year": year,
        "high_conf_only": high_conf_only,
        "total_ac": total_ac,
        "countries": countries,
        "committees": committees,
    }


def get_trend_overview(
    high_conf_only: bool = True,
) -> Dict[str, Any]:
    """
    LLM-friendly “trend overview”:
    Summarizes commonly used global statistics in a compact structure.
    Avoids sending overly large JSON blobs at once.
    """
    if high_conf_only:
        year_stats = get_ac_year_stats_high_conf()
    else:
        year_stats = get_ac_year_stats_all()

    # Global top affiliations / countries
    top_affs = get_top_affiliations_high_conf(limit=20)
    top_countries = get_top_countries_overall(
        limit=20,
        high_conf_only=high_conf_only,
    )

    return {
        "high_conf_only": high_conf_only,
        "ac_year_stats": year_stats,
        "top_affiliations": top_affs,
        "top_countries": top_countries,
    }
