#!/usr/bin/env python3
"""
从统计局社零发布页面的 XLS 附件批量提取分品类同比增速
- 翻页收集所有历史URL
- 下载XLS用pandas解析
- 输出完整的分品类历史数据
"""
import re, requests, time, json, os, io
from collections import OrderedDict

BASE = "https://www.stats.gov.cn/sj/zxfb/"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.stats.gov.cn/sj/zxfb/',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

# XLS中品类行名 → 标准名
ROW_TO_CAT = {
    '粮油、食品类': '粮油食品', '饮料类': '饮料', '烟酒类': '烟酒',
    '服装、鞋帽、针纺织品类': '服装鞋帽', '化妆品类': '化妆品',
    '金银珠宝类': '金银珠宝', '日用品类': '日用品',
    '体育、娱乐用品类': '体育娱乐', '家用电器和音像器材类': '家用电器',
    '中西药品类': '中西药品', '文化办公用品类': '文化办公',
    '家具类': '家具', '通讯器材类': '通讯器材',
    '石油及制品类': '石油制品', '汽车类': '汽车',
    '建筑及装潢材料类': '建筑装潢',
}


def title_to_key(title: str):
    """从标题解析数据月份 'YYYY-MM'
    兼容两种标题：
      - 单月: '2025年12月份社会消费品零售总额...'        -> 2025-12
      - 累计: '2026年1—5月份社会消费品零售总额...'       -> 2026-05 (取末月)
    """
    m = re.search(r'(\d{4})年(\d{1,2})[—–\-](\d{1,2})月', title)
    if m:
        return f"{m.group(1)}-{int(m.group(3)):02d}"
    m = re.search(r'(\d{4})年(\d{1,2})月', title)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}"
    return None


def find_retail_urls(max_pages: int = 80):
    """翻页收集所有社零发布URL"""
    urls = OrderedDict()
    for page in range(0, max_pages):
        url = BASE + (f"index_{page}.html" if page > 0 else "index.html")
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.encoding = 'utf-8'
            if r.status_code != 200:
                break
        except Exception:
            break
        for m in re.finditer(r'<a\s[^>]*href="(\./[^"]+\.html)"[^>]*>([^<]*社会消费品零售总额[^<]*)</a>', r.text):
            href, title = m.group(1), m.group(2)
            full = BASE + href[2:] if href.startswith('./') else href
            k = title_to_key(title)
            if k and k not in urls:
                urls[k] = full
        print(f"  第{page}页: {len(urls)}个URL", flush=True)
        time.sleep(0.2)
    return urls


def parse_xls_attachment(page_url):
    """下载并解析发布页面附带的XLS文件"""
    from urllib.parse import urljoin
    # 抓取发布页（站点偶发返回不含附件的缓存/防护页，故重试几次）
    m = None
    for _ in range(4):
        try:
            r = requests.get(page_url, headers=HEADERS, timeout=15)
            r.encoding = 'utf-8'
            m = re.search(r'href="([^"]+\.xls[x]?[^"]*)"', r.text)
            if m:
                break
        except Exception:
            pass
        time.sleep(0.6)
    if not m:
        return None
    xls_url = urljoin(page_url, m.group(1))
    
    # 下载附件（带一次重试）
    content = None
    for _ in range(2):
        try:
            r = requests.get(xls_url, headers={**HEADERS, 'Referer': page_url}, timeout=20)
            if r.status_code == 200 and len(r.content) > 1000:
                content = r.content
                break
        except Exception:
            pass
        time.sleep(0.5)
    if content is None:
        return None

    # 按文件头选择引擎，依次兜底：xlrd(.xls) / openpyxl(.xlsx) / 自动
    import pandas as pd
    head = content[:8]
    if head[:4] == b'\xd0\xcf\x11\xe0':
        engines = ['xlrd', None]            # OLE2 -> 老式 .xls
    elif head[:2] == b'PK':
        engines = ['openpyxl', None]        # ZIP -> .xlsx
    else:
        engines = ['xlrd', 'openpyxl', None]
    dfs = None
    last_err = None
    for eng in engines:
        try:
            dfs = pd.read_excel(io.BytesIO(content), sheet_name=None, engine=eng) if eng \
                else pd.read_excel(io.BytesIO(content), sheet_name=None)
            break
        except Exception as e:
            last_err = e
    if dfs is None:
        print(f"    XLS解析失败: {last_err}", flush=True)
        return None
    
    # 提取分品类数据：品类在第0列，当月同比在第2列
    df = list(dfs.values())[0]
    cats = {}
    for _, row in df.iterrows():
        name = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ''
        std = ROW_TO_CAT.get(name)
        if not std:
            continue
        try:
            yoy = float(row.iloc[2])
            if -99 < yoy < 500:
                cats[std] = yoy
        except (ValueError, TypeError):
            continue
    return cats if cats else None


def main():
    print("=" * 60, flush=True)
    print("社零分品类数据批量采集 (XLS版)", flush=True)
    print("=" * 60, flush=True)
    
    # 1. 收URL
    print("\n[1] 翻页收集发布URL...")
    urls = find_retail_urls()
    print(f"  共找到 {len(urls)} 个URL\n")
    
    # 2. 解析XLS
    print("[2] 下载XLS并解析分品类数据...")
    category_data = OrderedDict()
    source_urls = {}
    
    for dk, url in sorted(urls.items()):
        print(f"  {dk}...", end=" ", flush=True)
        cats = parse_xls_attachment(url)
        if cats:
            category_data[dk] = cats
            source_urls[dk] = url
            print(f"✅ {len(cats)}个品类")
        else:
            print(f"⚠️ 未获取")
        time.sleep(0.5)
    
    print(f"\n  成功: {len(category_data)}/{len(urls)}")
    
    # 3. 与已有历史合并后保存（避免覆盖丢失已抓取月份）
    base = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base, "results", "retail_category_history.json")
    os.makedirs(os.path.dirname(json_path), exist_ok=True)

    merged_data = OrderedDict()
    merged_urls = {}
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                old = json.load(f)
            merged_data.update(old.get("data", {}))
            merged_urls.update(old.get("source_urls", {}))
        except Exception:
            pass
    # 本次抓取的新数据覆盖/补充旧数据
    merged_data.update(category_data)
    merged_urls.update(source_urls)
    merged_data = OrderedDict(sorted(merged_data.items()))
    merged_urls = {k: merged_urls[k] for k in sorted(merged_urls)}

    output = {
        "generated_at": __import__('datetime').datetime.now().isoformat(),
        "data": merged_data,
        "source_urls": merged_urls,
    }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 已保存: {json_path}")
    print(f"   本次抓取 {len(category_data)} 个月, 合并后共 {len(merged_data)} 个月")
    for dk in sorted(merged_data.keys()):
        print(f"     {dk} -> {merged_urls.get(dk, '?')}")


if __name__ == "__main__":
    main()
