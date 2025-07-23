#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import csv
import requests
import re
from bs4 import BeautifulSoup, Tag, NavigableString

# ---------------- Configuration ----------------
OUTPUT_CSV = os.path.join("data", "raw", "committee_members.csv")
START_YEAR = 2011
END_YEAR   = 2025
USER_AGENT = "Mozilla/5.0 (compatible; Bot/0.1; +https://your.site/)"

def fetch_url(url):
    headers = {"User-Agent": USER_AGENT}
    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    return r.text

def scrape_chi_2011():
    url = "http://chi2011.org/authors/selecting-subcommittee.html"
    html = fetch_url(url)
    soup = BeautifulSoup(html, "html.parser")

    # 定位到真正的主内容区
    container = soup.select_one("div#main-text-single-col")
    if not container:
        print("[WARN] CHI 2011: 找不到主体区域")
        return []

    results = []
    # 每个版块的标题是 <h5><span id="...">版块名称</span></h5>
    for h5 in container.find_all("h5"):
        span = h5.find("span", id=True)
        if not span:
            continue
        sub_name = span.get_text(strip=True)

        # 跳过所有空行，直接找到第一个包含 “Associate Chairs” 字样的 <p>
        ac_p = h5.find_next_sibling(lambda t: isinstance(t, Tag)
                                           and t.name == "p"
                                           and "Associate Chairs" in t.get_text())
        if not ac_p:
            continue

        # 只取这个 <p> 中直接子节点的 <a>（不跨过其他层级）
        for a in ac_p.find_all("a", recursive=False):
            name = a.get_text(strip=True)
            if name:
                results.append((2011, sub_name, name))

    print(f"[OK]   CHI 2011: got {len(results)} rows")
    return results



def scrape_chi_2012():
    url = "https://chi2012.acm.org/cfp-selecting-subcommittee.shtml"
    try:
        html = fetch_url(url)
    except Exception as e:
        print(f"[WARN] CHI 2012: 无法访问页面 ({e})，跳过")
        return []
    
    soup = BeautifulSoup(html, "html.parser")
    container = soup.select_one("div.container div.content#content")
    if not container:
        print("[WARN] CHI 2012: 找不到主体区域，请检查 selector")
        return []
    
    results = []
    skip_ids = {"introduction", "guidance", "list-of-the-subcommittees"}
    for h2 in container.find_all("h2", id=True):
        if h2["id"] in skip_ids:
            continue
        sub_name = h2.get_text(strip=True)
        
        # 定位到 Associate Chairs:
        ac_strong = h2.find_next(
            lambda t: isinstance(t, Tag)
                      and t.name == "strong"
                      and "associate chairs" in t.get_text(strip=True).lower()
        )
        if not ac_strong:
            continue
        
        # 整个 <p> 里既有 Chairs: 部分，也有 Associate Chairs: 部分
        parent_p = ac_strong.find_parent("p")
        
        # 只从 Associate Chairs: 之后开始取
        in_ac_list = False
        for node in parent_p.contents:
            # 如果又碰到 <strong>，检查一下是 Chairs 还是 Associate Chairs
            if isinstance(node, Tag) and node.name == "strong":
                txt = node.get_text(strip=True).lower()
                in_ac_list = txt.startswith("associate chairs")
                continue
            
            if not in_ac_list:
                # 还没到副主席那一节，就跳过
                continue
            
            # 只处理文本节点，跳过 <br>、<strong> 等
            if isinstance(node, NavigableString):
                name = node.strip().strip('“”" ,')
                if name:
                    results.append((2012, sub_name, name))
        
    print(f"[OK]   CHI 2012: got {len(results)} rows")
    return results



def scrape_chi_2013():
    url = ("https://chi2013.acm.org/authors/call-for-participation/papers-notes/selecting-a-subcommittee")
    html = fetch_url(url)
    soup = BeautifulSoup(html, "html.parser")

    # 1. 定位正文容器
    entry = soup.select_one("div#post-316 .entry-content")
    if not entry:
        print("[WARN] CHI 2013: 找不到 entry-content")
        return []

    # 2. 定位到 “Subcommittee membership” 段
    h2 = entry.find("h2", string=re.compile(r"Subcommittee membership", re.I))
    if not h2:
        print("[WARN] CHI 2013: 找不到 Subcommittee membership 标题")
        return []

    results = []
    sib = h2

    # 3. 从这个 H2 开始，依次查找后面的 <h3> + <table>
    while True:
        sib = sib.find_next_sibling()
        if not sib:
            break

        # 只处理 <h3> 作为小节
        if sib.name != "h3":
            continue

        full_title = sib.get_text(strip=True)
        # 去掉尾部 “subcommittee”
        sub_name = re.sub(r"\s*subcommittee$", "", full_title, flags=re.I)

        # 4. 找到紧跟的那张表
        tbl = sib.find_next_sibling("table", class_="tableizer-table")
        if not tbl:
            continue

        # 5. 遍历表格每一行（跳过首行表头）
        rows = tbl.select("tbody tr")[1:]
        for tr in rows:
            tds = tr.find_all("td")
            if len(tds) < 3:
                continue
            name = tds[0].get_text(strip=True)
            position = tds[2].get_text(strip=True)
            # 只保留 Associate Chair (AC)
            if re.fullmatch(r"AC", position, re.I):
                results.append((2013, sub_name, name))

    print(f"[OK]   CHI 2013: got {len(results)} rows")
    return results


def scrape_chi_2014to2015(year):
    # 2014/2015 的 URL 都不要末尾斜杠
    url = f"https://chi{year}.acm.org/authors/selecting-a-subcommittee"
    try:
        html = fetch_url(url)
    except Exception as e:
        print(f"[WARN] CHI {year}: 无法访问页面 ({e})，跳过")
        return []

    soup = BeautifulSoup(html, "html.parser")
    # 2014 用 #content-canvas，2015 用 .container .column-main
    if year == 2014:
        container = soup.select_one("div#content-canvas")
    else:
        container = soup.select_one("div.container div.column-main")
    if not container:
        print(f"[WARN] CHI {year}: 找不到主内容区，请检查 selector")
        return []

    results = []
    # 每个小节由 <h4 id="..."> 分割
    for h4 in container.find_all("h4", id=True):
        sub_name = h4.get_text(strip=True)

        # 找到紧跟的“Subcommittee:”那行
        sc_strong = h4.find_next(
            lambda t: isinstance(t, Tag)
                      and t.name == "strong"
                      and "subcommittee" in t.get_text(strip=True).lower()
        )
        if not sc_strong:
            continue

        # 从这个 <strong> 所在的 <p>，取它后面的第一个兄弟 <p>
        sc_p = sc_strong.find_parent("p").find_next_sibling("p")
        if not sc_p:
            continue

        # 这个 <p> 里的内容是若干个文本节点/引号，再配合 <br> 分段
        buf = []
        def flush_buf():
            name = "".join(buf).strip().strip('“”"')
            if name:
                results.append((year, sub_name, name))
        for node in sc_p.children:
            if isinstance(node, Tag) and node.name == "br":
                flush_buf()
                buf = []
            else:
                text = ""
                if isinstance(node, NavigableString):
                    text = node.strip()
                elif isinstance(node, Tag):
                    text = node.get_text(strip=True)
                buf.append(text)
        # 最后一段
        flush_buf()

    print(f"[OK]   CHI {year}: got {len(results)} rows")
    return results







def scrape_chi_2016():
    url = "https://chi2016.acm.org/wp/guide-to-selecting-a-subcommittee-for-submission/"
    try:
        html = fetch_url(url)
    except Exception:
        print("[WARN] CHI 2016: 访问失败或页面不存在，跳过")
        return []

    soup = BeautifulSoup(html, "html.parser")
    container = soup.select_one("div.single_inside_content")
    if not container:
        print("[WARN] CHI 2016: 找不到内容容器，请确认 selector")
        return []

    results = []
    skip_titles = {
        "list of the subcommittees",
        "overview",
        "subcommittee selection process",
    }

    for h2 in container.find_all("h2"):
        title = h2.get_text(strip=True)
        if title.lower() in skip_titles:
            continue
        sub_name = title

        # 找到 “Associate Chairs:” 那行
        ac_tag = None
        for sib in h2.next_siblings:
            if isinstance(sib, Tag) and sib.name == "h2":
                break
            if (isinstance(sib, Tag)
                and sib.name == "p"
                and sib.find("strong")
                and "associate chairs" in sib.get_text(strip=True).lower()):
                ac_tag = sib
                break
        if not ac_tag:
            continue

        # 拿到紧跟的那个 <p>，它内里通过 <a> + <br> 或纯文本记录所有成员
        members_p = ac_tag.find_next_sibling(lambda t: isinstance(t, Tag) and t.name=="p")
        if not members_p:
            continue

        # 我们先把整段用 <br> 拆开
        segments = []
        buf = []
        for node in members_p.children:
            if isinstance(node, Tag) and node.name == "br":
                # 一段结束
                segment = "".join(buf).strip()
                if segment:
                    segments.append(segment)
                buf = []
            else:
                # 文本节点或 <a>
                text = ""
                if isinstance(node, NavigableString):
                    text = node.strip()
                elif isinstance(node, Tag):
                    text = node.get_text(strip=True)
                buf.append(text)
        # 最后一段
        last = "".join(buf).strip()
        if last:
            segments.append(last)

        # 过滤空项 & “Associate Chairs:” 等
        for seg in segments:
            seg = seg.strip(' ,\n')
            if not seg:
                continue
            # 有时候会出现前面多余的逗号或“Associate Chairs”
            clean = seg
            if clean.lower().startswith("associate chairs"):
                continue
            # 最终应该形如 "姓名, 单位"
            results.append((2016, sub_name, clean))

    print(f"[OK]   CHI 2016: got {len(results)} rows")
    return results

def scrape_chi_2017():
    url = "https://chi2017.acm.org/select-subcommittee.html"
    try:
        html = fetch_url(url)
    except Exception:
        print("[WARN] CHI 2017: 页面访问失败，跳过")
        return []

    soup = BeautifulSoup(html, "html.parser")
    results = []

    # 用锚点 <a class="myanchor" name="..."> 来划分子版块
    anchors = soup.find_all("a", class_="myanchor", attrs={"name": True})
    for anc in anchors:
        sub_name = anc["name"]  # slug 形式，比如 "user-experience-and-usability"
        # 在同一版块里，先找那行 Associate Chairs
        ac_p = None
        sib = anc
        while True:
            sib = sib.find_next_sibling()
            if not sib:
                break
            # 如果遇到下一个小节的锚点，就结束
            if isinstance(sib, Tag) and sib.name=="a" and "myanchor" in sib.get("class", []):
                break
            # 找到标记 Associate Chairs 的 <p>
            if isinstance(sib, Tag) and sib.name=="p":
                span = sib.find("span", class_="MyBolding")
                if span and re.search(r"associate chairs", span.get_text(), re.I):
                    ac_p = sib
                    break
        if not ac_p:
            continue

        # 从 Associate Chairs 那行的下一个节点开始，收集所有 “姓名, 单位” 形式的 <p>
        sib2 = ac_p
        while True:
            sib2 = sib2.find_next_sibling()
            if not sib2: 
                break
            if isinstance(sib2, Tag):
                # 碰到新的锚点就结束
                if sib2.name=="a" and "myanchor" in sib2.get("class", []):
                    break
                if sib2.name=="p":
                    text = sib2.get_text(" ", strip=True)
                    # 跳过空行和标题行
                    if not text or re.search(r"associate chairs", text, re.I):
                        continue
                    # 只要包含逗号，就认为是 “姓名, 单位”
                    if "," in text:
                        results.append((2017, sub_name, text))
        # 下一锚点继续

    print(f"[OK]   CHI 2017: got {len(results)} rows")
    return results

def scrape_chi_2018to2020(year):
    if year == 2018:
        url = "https://chi2018.acm.org/papers/selecting-a-subcommittee/"
        post_id = "524"
    elif year == 2019:
        url = "https://chi2019.acm.org/papers/selecting-a-subcommittee/"
        post_id = "215"
    else:  # 2020
        url = "https://chi2020.acm.org/authors/papers/selecting-a-subcommittee/"
        post_id = "215"

    try:
        html = fetch_url(url)
    except:
        print(f"[WARN] CHI {year}: 访问失败，跳过")
        return []

    soup = BeautifulSoup(html, "html.parser")
    post = soup.select_one(f"div#post-{post_id}")
    if not post:
        print(f"[WARN] CHI {year}: 找不到 post-{post_id}")
        return []

    results = []
    for sub_h3 in post.find_all("h3", id=True):
        sub_name = sub_h3.get_text(strip=True)
        sib = sub_h3
        ac_block = None

        while True:
            sib = sib.find_next_sibling()
            if not sib or (sib.name=="h3" and sib.has_attr("id")):
                break
            # 找 <p><strong>Associate Chairs</strong></p> 或 <p><b>Associate Chairs</b></p>
            if sib.name=="p" and sib.find(lambda t: t.name in ("strong","b") and "associate chairs" in t.get_text(strip=True).lower()):
                ac_block = sib
                break

        if not ac_block:
            continue

        lst = ac_block.find_next_sibling(lambda t: t.name in ("ul","ol"))
        if not lst:
            continue

        for li in lst.find_all("li"):
            results.append((year, sub_name, li.get_text(" ", strip=True)))

    print(f"[OK]   CHI {year}: got {len(results)} rows")
    return results


def scrape_chi_2021():
    url = "https://chi2021.acm.org/for-authors/presenting/papers/selecting-a-subcommittee/"
    html = fetch_url(url)
    soup = BeautifulSoup(html, "html.parser")

    container = soup.select_one("div.post-entry")
    if not container:
        print("[WARN] CHI 2021: 找不到主内容区")
        return []

    results = []
    # 所有带 id 的 <h4> 都是各 subcommittee 标题
    for sub_h4 in container.find_all("h4", id=True):
        sub_name = sub_h4.get_text(strip=True)
        # 往下找第一个 “Associate Chairs” <h4>
        sib = sub_h4
        ac_h4 = None
        while True:
            sib = sib.find_next_sibling()
            if not sib or (sib.name=="h4" and sib.has_attr("id")):
                # 撞到下一个 subcommittee 或无更多节点，就停
                break
            if sib.name=="h4" and "associate chairs" in sib.get_text(strip=True).lower():
                ac_h4 = sib
                break

        if not ac_h4:
            continue
        ul = ac_h4.find_next_sibling("ul")
        if not ul:
            continue

        for li in ul.find_all("li"):
            name = li.get_text(" ", strip=True)
            results.append((2021, sub_name, name))

    print(f"[OK]   CHI 2021: got {len(results)} rows")
    return results


def scrape_chi_2022():
    url = "https://chi2022.acm.org/subcommittees/selecting-a-subcommittee/"
    try:
        html = fetch_url(url)
    except Exception:
        print("[WARN] CHI 2022: 域名解析或网络错误，跳过")
        return []

    soup = BeautifulSoup(html, "html.parser")
    container = soup.select_one("div.entry-content")
    if not container:
        print("[WARN] CHI 2022: 找不到主内容区")
        return []

    results = []
    for h3 in container.find_all("h3", id=True):
        sub = h3.get_text(strip=True)
        block = h3.find_next_sibling("div", class_="insert-page")
        if not block: continue

        ac = block.find(lambda t: t.name=="h4" 
                        and "associate chairs" in t.get_text(strip=True).lower())
        if not ac: continue

        ul = ac.find_next_sibling("ul")
        if not ul: continue

        for li in ul.find_all("li"):
            results.append((2022, sub, li.get_text(" ", strip=True)))

    print(f"[OK]   CHI 2022: got {len(results)} rows")
    return results


# ---------------- 专门处理 CHI 2023 ----------------
def scrape_chi_2023():
    url = "https://chi2023.acm.org/subcommittees/selecting-a-subcommittee/"
    html = fetch_url(url)
    soup = BeautifulSoup(html, "html.parser")

    container = soup.select_one("div.entry-content.clearfix")
    if not container:
        print("[WARN] CHI 2023: 找不到主内容区")
        return []

    results = []
    for h2 in container.find_all("h2", id=True):
        sub_name = h2.get_text(strip=True)
        block = h2.find_next_sibling("div", class_="insert-page")
        if not block:
            continue

        # 找 “Associate Chairs” 标题
        ac_h3 = block.find(
            lambda tag: tag.name=="h3"
                        and "associate chairs" in tag.get_text(strip=True).lower()
        )
        if not ac_h3:
            continue

        # 紧跟的 <ul> 里面的 <li> 就是成员
        ul = ac_h3.find_next_sibling("ul")
        if not ul:
            continue

        for li in ul.find_all("li"):
            name = li.get_text(" ", strip=True)
            results.append((2023, sub_name, name))

    print(f"[OK]   CHI 2023: got {len(results)} rows")
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
        print(f"[OK]   CHI {year}: got {len(results)} rows")
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
            if yr == 2011:
                rows = scrape_chi_2011()
            elif yr == 2012:
                rows = scrape_chi_2012()
            elif yr == 2013:
                rows = scrape_chi_2013()
            elif yr == yr in (2014, 2015):
                rows = scrape_chi_2014to2015(yr)
            elif yr == 2016:
                rows = scrape_chi_2016()
            elif yr == 2017:
                rows = scrape_chi_2017()
            elif yr in (2018, 2019, 2020):
                rows = scrape_chi_2018to2020(yr)
            elif yr == 2021:
                rows = scrape_chi_2021()
            elif yr == 2021:
                rows = scrape_chi_2021()
            elif yr == 2022:
                rows = scrape_chi_2022()
            elif yr == 2023:
                rows = scrape_chi_2023()
            else:
                rows = scrape_chi_year(yr)

            for y, c, m in rows:
                w.writerow([y, "CHI", c, m])
            time.sleep(1)

    print("🎉 完成，输出在", OUTPUT_CSV)

if __name__ == "__main__":
    main()
