#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, time, csv, requests, re
from bs4 import BeautifulSoup

# ---------------- Configuration ----------------
OUTPUT_CSV = "data/raw/committee_members.csv"
START_YEAR = 2023
END_YEAR   = 2025
USER_AGENT = "Mozilla/5.0 (compatible; Bot/0.1; +https://your.site/)"

def fetch_url(url):
    headers = {"User-Agent": USER_AGENT}
    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    return r.text

# ---------------- 专门处理 CHI 2023 ----------------
def scrape_chi_2023():
    base_url = "https://chi2023.acm.org"
    index_url = f"{base_url}/subcommittees/selecting-a-subcommittee/"
    html = fetch_url(index_url)
    soup = BeautifulSoup(html, "html.parser")

    container = soup.select_one("div.entry-content.clearfix")
    if not container:
        print(f"[WARN] CHI 2023: 无法定位主容器")
        return []

    results = []

    for a in container.find_all("a", class_="insert-page"):
        subcommittee_name = a.get_text(strip=True)
        page_id = a.get("data-post-id")
        if not page_id:
            continue

        sub_url = f"{base_url}/?post_type=page&p={page_id}"
        try:
            sub_html = fetch_url(sub_url)
            sub_soup = BeautifulSoup(sub_html, "html.parser")

            for h3 in sub_soup.find_all("h3"):
                if "associate chairs" in h3.get_text(strip=True).lower():
                    ul = h3.find_next_sibling("ul")
                    if not ul:
                        continue
                    for li in ul.find_all("li"):
                        name = li.get_text(" ", strip=True)
                        results.append((2023, subcommittee_name, name))
        except Exception as e:
            print(f"[ERR] 子页面失败: {sub_url} -- {e}")

        time.sleep(0.2)

    print(f"[OK]   CHI 2023: got {len(results)} rows from insert-pages")
    return results

# ---------------- 处理 CHI 2024+ ----------------
def scrape_chi_year(year):
    url = f"https://chi{year}.acm.org/subcommittees/selecting-a-subcommittee/"
    html = fetch_url(url)
    soup = BeautifulSoup(html, "html.parser")

    container = soup.select_one("div.entry-content.clearfix")
    if not container:
        print(f"[WARN] CHI {year}: 无法定位主容器，跳过")
        return []

    results = []

    h2s = []
    for h2 in container.find_all("h2", id=True):
        t = h2.get_text(strip=True).lower()
        if any(skip in t for skip in (
            "overview","composition","selecting a subcommittee","list of the subcommittees"
        )):
            continue
        h2s.append(h2)

    if h2s:
        for h2 in h2s:
            cname = h2.get_text(strip=True)
            sib = h2
            while True:
                sib = sib.find_next_sibling()
                if not sib or sib.name == "h2":
                    break
                if sib.name == "h3":
                    h3_text = sib.get_text(strip=True).lower()
                    if h3_text.startswith("associate chairs"):
                        ul = sib.find_next("ul")
                        if not ul:
                            continue
                        for li in ul.find_all("li"):
                            name = li.get_text(" ", strip=True)
                            results.append((year, cname, name))
        print(f"[OK]   CHI {year}: new style, got {len(results)} rows")
        return results

    print(f"[OK]   CHI {year}: 抓取到 {len(results)} 条 Associate Chairs")
    return results

# ---------------- 其他顶会 ----------------
def scrape_uist_year(year):
    return []

def scrape_cscw_year(year):
    return []

# ---------------- Main ----------------
def main():
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["year","venue","committee","member"])

        for yr in range(START_YEAR, END_YEAR+1):
            if yr == 2023:
                for y, c, m in scrape_chi_2023():
                    w.writerow([y, "CHI", c, m])
            else:
                for y, c, m in scrape_chi_year(yr):
                    w.writerow([y, "CHI", c, m])
            time.sleep(1)

    print("🎉 完成，输出在", OUTPUT_CSV)

if __name__ == "__main__":
    main()