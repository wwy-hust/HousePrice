#!/usr/bin/env python3
"""
规模以上工业企业数据采集
- 营业收入同比增速（累积）
- 产成品存货同比增速
数据来源：国家统计局月度发布 "规模以上工业企业利润"
"""
import requests, re, time, json, os, io
from urllib.parse import urljoin
from collections import OrderedDict

BASE = "https://www.stats.gov.cn/sj/zxfb/"
BASE2 = "https://www.stats.gov.cn/zwfwck/sjfb/"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Referer': 'https://www.stats.gov.cn/sj/zxfb/',
}


def find_industry_urls():
    """翻页收集所有工业企业利润发布URL"""
    urls = OrderedDict()
    for prefix in [BASE, BASE2]:
        for page in range(0, 70):
            url = prefix + (f"index_{page}.html" if page > 0 else "index.html")
            try:
                r = requests.get(url, headers=HEADERS, timeout=15)
                r.encoding = 'utf-8'
                if r.status_code != 200:
                    break
            except:
                break
            for m in re.finditer(r'<a\s[^>]*href="(\./[^"\.]+\.html)"[^>]*>([^<]*规[模上工业企利润][^<]*)</a>', r.text):
                href, title = m.group(1), m.group(2).strip()
                if '规模以上工业企业利润' not in title:
                    continue
                full = urljoin(prefix, href)
                dm = re.search(r'(\d{4})年\D*(\d{1,2})[—–\-](\d{1,2})?月?', title)
                if dm:
                    end_m = dm.group(3) or dm.group(2)
                    key = f"{dm.group(1)}-{int(end_m):02d}"
                else:
                    continue
                if key not in urls:
                    urls[key] = full
            time.sleep(0.3)
    return urls


def parse_industry_page(page_url):
    """解析页面，提取营收增速和存货增速"""
    try:
        r = requests.get(page_url, headers=HEADERS, timeout=15)
        r.encoding = 'utf-8'
    except:
        return None
    
    html = r.text
    result = {}
    
    # 方法1: 从XLS附件解析
    m = re.search(r'href="(\./[^"]*\.xls[^"]*)"', html)
    if m:
        try:
            import pandas as pd
            xls_url = urljoin(page_url, m.group(1))
            xr = requests.get(xls_url, headers={**HEADERS, 'Referer': page_url}, timeout=20)
            dfs = pd.read_excel(io.BytesIO(xr.content))
            
            # 找 "总计" 行的 "营业收入-同比增长" 列
            for _, row in dfs.iterrows():
                name = str(row.iloc[0]).strip()
                if name == '总计':
                    try:
                        result['revenue_yoy'] = float(row.iloc[2])  # 第3列 = 营收同比
                    except:
                        pass
                    break
        except Exception:
            pass
    
    # 方法2: 从HTML文本用正则提取
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text)
    
    if 'revenue_yoy' not in result:
        # 营业收入 同比增长
        m = re.search(r'营业收入.*?同比增长\s*(-?\d+\.?\d*)\s*%', text)
        if not m:
            m = re.search(r'实现营业收入.*?同比增长\s*(-?\d+\.?\d*)\s*%', text)
        if m:
            result['revenue_yoy'] = float(m.group(1))
    
    # 产成品存货增速
    m = re.search(r'产成品存货.*?增[长加]\s*(-?\d+\.?\d*)\s*%', text)
    if m:
        result['inventory_yoy'] = float(m.group(1))
    else:
        m = re.search(r'产成品存货.*?增[长加].*?(-?\d+\.?\d*)%', text)
        if m:
            result['inventory_yoy'] = float(m.group(1))
    
    return result if result else None


def main():
    print("=" * 60, flush=True)
    print("规模以上工业企业数据采集", flush=True)
    print("=" * 60, flush=True)
    
    # 1. 收集URL
    print("\n[1] 翻页收集发布URL...", flush=True)
    urls = find_industry_urls()
    print(f"  共找到 {len(urls)} 个URL", flush=True)
    for k in sorted(urls.keys())[:20]:
        print(f"    {k} -> {urls[k]}")
    
    # 2. 解析数据
    print(f"\n[2] 解析数据...", flush=True)
    revenue = OrderedDict()
    inventory = OrderedDict()
    source_urls = OrderedDict()
    ok = 0
    
    for dk, url in sorted(urls.items()):
        data = parse_industry_page(url)
        if data:
            revenue[dk] = data.get('revenue_yoy')
            inventory[dk] = data.get('inventory_yoy')
            source_urls[dk] = url
            ok += 1
            rev_str = f"{data.get('revenue_yoy', 'N/A')}%" if data.get('revenue_yoy') is not None else 'N/A'
            inv_str = f"{data.get('inventory_yoy', 'N/A')}%" if data.get('inventory_yoy') is not None else 'N/A'
            print(f"  {dk}: 营收{rev_str}, 存货{inv_str}", flush=True)
        else:
            print(f"  {dk}: 未获取", flush=True)
        time.sleep(0.5)
    
    print(f"\n  成功: {ok}/{len(urls)}", flush=True)
    
    # 3. 生成JSON
    result = {
        "data_type": "规模以上工业企业",
        "generated_at": __import__('datetime').datetime.now().isoformat(),
        "data_source": "国家统计局",
        "revenue_yoy": {k: v for k, v in revenue.items()},
        "inventory_yoy": {k: v for k, v in inventory.items()},
        "source_urls": {k: v for k, v in source_urls.items()},
    }
    
    base = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base, "results", "industry_data.json")
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 已保存: {json_path}")
    print(f"   营收数据点: {len([v for v in revenue.values() if v is not None])}")
    print(f"   存货数据点: {len([v for v in inventory.values() if v is not None])}")


if __name__ == "__main__":
    main()
