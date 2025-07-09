#!/usr/bin/env python3

import os
import argparse
import requests
import pandas as pd
from tqdm import tqdm

def reconstruct_abstract(inv_idx):
    try:
        pos_token = []
        for token, positions in inv_idx.items():
            for p in positions:
                pos_token.append((p, token))
        pos_token.sort()
        return ' '.join([tok for _, tok in pos_token])
    except Exception:
        return None

def fetch_openalex_works(start_year, end_year, per_page, mailto):
    url = "https://api.openalex.org/works"
    all_records = []
    concept_filter = "concept.id:C41008148"

    for year in range(start_year, end_year + 1):
        print(f"Fetching {year}...")
        cursor = "*"
        while cursor:
            params = {
                "filter": f"{concept_filter},from_publication_date:{year}-01-01,to_publication_date:{year}-12-31",
                "per-page": per_page,
                "cursor": cursor,
                "mailto": mailto
            }
            resp = requests.get(url, params=params)
            if resp.status_code != 200:
                print(f"Error {resp.status_code} for year {year}")
                break
            data = resp.json()
            for item in data.get("results", []):
                inv_idx = item.get("abstract_inverted_index") or {}
                abstract = reconstruct_abstract(inv_idx) if inv_idx else None

                authors = "; ".join(
                    a["author"]["display_name"]
                    for a in item.get("authorships", [])
                )

                insts = set()
                for a in item.get("authorships", []):
                    for inst in a.get("institutions", []):
                        insts.add(inst.get("display_name"))
                institutions = "; ".join(insts) if insts else None

                concepts = "; ".join(
                    c.get("display_name")
                    for c in item.get("concepts", [])
                )

                record = {
                    "title": item.get("title"),
                    "authors": authors,
                    "institutions": institutions,
                    "year": item.get("publication_year"),
                    "venue": item.get("host_venue", {}).get("display_name"),
                    "doi": item.get("doi"),
                    "citation_count": item.get("cited_by_count"),
                    "abstract": abstract,
                    "concepts": concepts,
                    "url": item.get("primary_location", {}).get("landing_page_url")
                }
                all_records.append(record)

            cursor = data.get("meta", {}).get("next_cursor")

    return pd.DataFrame(all_records)

def main():
    parser = argparse.ArgumentParser(description="Crawl OpenAlex for HCI works and save to CSV")
    parser.add_argument("--start-year", type=int, default=2020)
    parser.add_argument("--end-year", type=int, default=2024)
    parser.add_argument("--output", type=str, default="data/raw/hci_works.csv")
    parser.add_argument("--per-page", type=int, default=200)
    parser.add_argument("--mailto", type=str, required=True)
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    if os.path.exists(args.output):
        existing = pd.read_csv(args.output)
        years_done = set(existing['year'].unique())
    else:
        existing = pd.DataFrame()
        years_done = set()

    df_new = fetch_openalex_works(args.start_year, args.end_year, args.per_page, args.mailto)
    df_new = df_new[~df_new['year'].isin(years_done)]

    df_combined = pd.concat([existing, df_new], ignore_index=True)
    df_combined.drop_duplicates(subset=['doi'], inplace=True)
    df_combined.to_csv(args.output, index=False)
    print(f"Saved {len(df_combined)} records to {args.output}")

if __name__ == "__main__":
    main()
