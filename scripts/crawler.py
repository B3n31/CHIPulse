#!/usr/bin/env python3
"""
Fetch HCI-related works from OpenAlex via concepts.id, locally filter by venue substrings.
每抓到一条立即写 CSV 并打印到终端，方便调试。
"""
import os
import time
import csv
import requests
from tqdm import tqdm

# ---------------- Configuration ----------------
MAILTO     = "tza80@sfu.ca"   # <-- 替换成你的邮箱
START_YEAR = 2020             # 最早抓取年份
END_YEAR   = 2025             # 最晚抓取年份
OUTPUT_CSV = "data/raw/hci_works_full.csv"
PER_PAGE   = 200              # 每页最大条数（OpenAlex 限制）
RATE_LIMIT = 0.1              # 每页之间暂停时间（秒）
FILTER_STR = "concepts.id:C107457646"  # AR/VR/HCI 在 OpenAlex 的概念 ID

# 本地再次按会议或期刊名过滤，只保留核心 HCI 论坛
VENUE_SUBSTRINGS = [
    "CHI Conference on Human Factors",
    "Computer Supported Cooperative Work",
    "UIST",
    "Transactions on Computer-Human Interaction",
    "Designing Interactive Systems",
    "Intelligent User Interfaces",
    "Mobile Human-Computer Interaction",
    "Engineering Interactive Computing Systems",
    "Tangible, Embedded, and Embodied Interaction",
    "Human-Computer Interaction – INTERACT"
]

# CSV 列头
HEADERS = [
    "title","doi","year","venue","authors","institutions",
    "concepts","abstract","citation_count","counts_by_year",
    "cited_by_api_url","is_oa","pdf_url","landing_url"
]

# --------------- Helper Functions --------------
def reconstruct_abstract(inv_idx):
    """从 inverted index 重建 abstract 文本"""
    try:
        items = [(pos, tok) for tok, poses in inv_idx.items() for pos in poses]
        items.sort(key=lambda x: x[0])
        return " ".join(tok for _, tok in items)
    except:
        return None

# --------------- Main Logic --------------
def run():
    # 确保 data 目录存在
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    # 如果文件不存在就先写 header
    if not os.path.exists(OUTPUT_CSV):
        with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=HEADERS)
            writer.writeheader()

    base_url = "https://api.openalex.org/works"
    for year in range(START_YEAR, END_YEAR + 1):
        cursor = "*"
        pbar = tqdm(desc=f"Year {year}", unit="page")
        while cursor:
            params = {
                "filter": f"{FILTER_STR},"
                          f"from_publication_date:{year}-01-01,"
                          f"to_publication_date:{year}-12-31",
                "per-page": PER_PAGE,
                "cursor": cursor,
                "mailto": MAILTO
            }
            resp = requests.get(base_url, params=params)
            if resp.status_code != 200:
                print(f"[WARN] HTTP {resp.status_code} on year {year}, abort this year.")
                break
            data = resp.json()

            # 遍历每条结果，过滤 & 写入
            for item in data.get("results", []):
                host = item.get("host_venue") or {}
                pl   = item.get("primary_location") or {}
                src  = pl.get("source") or {}
                venue = (
                    host.get("display_name")
                    or src.get("display_name")
                    or ""
                )
                venue_l = venue.lower()
                # 只要列表里有任意一个子串（也小写）出现在 venue_l 里，就保留
                if not any(sub.lower() in venue_l for sub in VENUE_SUBSTRINGS):
                    continue

                # 构建 record
                inv_idx    = item.get("abstract_inverted_index") or {}
                abstract   = reconstruct_abstract(inv_idx) if inv_idx else None
                authors    = "; ".join(a["author"]["display_name"] for a in item.get("authorships", []))
                insts      = {
                    inst.get("display_name")
                    for a in item.get("authorships", [])
                    for inst in a.get("institutions", [])
                }
                institutions   = "; ".join(insts) if insts else None
                concepts       = "; ".join(c.get("display_name") for c in item.get("concepts", []))
                loc            = item.get("primary_location") or {}
                is_oa          = loc.get("is_oa", False)
                pdf_url        = loc.get("pdf_url")
                landing_url    = loc.get("landing_page_url")
                citation_count = item.get("cited_by_count")
                counts_by_year = item.get("counts_by_year")
                work_id        = item.get("id", "")
                cited_api_url  = f"https://api.openalex.org/works?filter=cites:{work_id}"

                record = {
                    "title": item.get("title"),
                    "doi": item.get("doi"),
                    "year": year,
                    "venue": venue,
                    "authors": authors,
                    "institutions": institutions,
                    "concepts": concepts,
                    "abstract": abstract,
                    "citation_count": citation_count,
                    "counts_by_year": counts_by_year,
                    "cited_by_api_url": cited_api_url,
                    "is_oa": is_oa,
                    "pdf_url": pdf_url,
                    "landing_url": landing_url
                }

                # 写入一行
                with open(OUTPUT_CSV, "a", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=HEADERS)
                    writer.writerow(record)


            # 翻页
            cursor = data.get("meta", {}).get("next_cursor")
            pbar.update(1)
            time.sleep(RATE_LIMIT)

        pbar.close()

    print(f"All done! CSV 路径：{OUTPUT_CSV}")

if __name__ == "__main__":
    run()