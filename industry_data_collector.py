#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规模以上工业企业数据采集
- 营业收入累计同比增速（2018年及以前口径为"主营业务收入"，2019年起为"营业收入"）
- 产成品存货同比增速

数据来源：国家统计局新版数据库（月度数据 -> 工业 -> 工业企业主要经济指标）
基础接口：https://data.stats.gov.cn/dg/website/publicrelease/web/external
历史可回溯至 1999 年（营收）/ 2001 年（存货），已收录数据库全部可得月份。

说明：旧版 easyquery.htm 接口自 2026 年起返回 403，本采集器已改用新版 UUID 接口。
同时轻量抓取"最新发布"页面，为最近月份补充"查看原文"链接（source_urls）。
"""
import requests
import re
import time
import json
import os
import urllib3
from urllib.parse import urljoin
from collections import OrderedDict

urllib3.disable_warnings()

# ---------------- 新版统计局数据库 API ----------------
NBS_BASE = 'https://data.stats.gov.cn/dg/website/publicrelease/web/external'
NBS_ROOT_MONTHLY = 'fc982599aa684be7969d7b90b1bd0e84'  # 月度数据根节点
# 叶子数据集：工业 -> 工业企业主要经济指标（规模以上工业企业）
CID_INDUSTRY = 'd760d189206642ce8afad57640408e09'
# 指标 ID（同一 cid 内稳定）
IND_REVENUE_NEW = '84117bfe6f1b4a299d0db210deb5ad36'  # 营业收入累计增长(%) 2019-02 起
IND_REVENUE_OLD = '2e4e354e7d664da2a5f549ad2452dd60'  # 主营业务收入累计增长(%) ~2018-12 止
IND_INVENTORY = 'e00c23ba6ffc45ae86757ce81f1c1997'    # 产成品存货增减(%)

NBS_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
    'Referer': 'https://data.stats.gov.cn/index.htm',
    'X-Requested-With': 'XMLHttpRequest',
}

# ---------------- 最新发布页（用于 source_urls 原文链接）----------------
ZXFB_BASE = "https://www.stats.gov.cn/sj/zxfb/"
ZXFB_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.stats.gov.cn/sj/zxfb/',
}


def _code_to_key(code):
    """'202606MM' -> '2026-06'"""
    m = re.match(r'(\d{4})(\d{2})', code)
    return f"{m.group(1)}-{m.group(2)}" if m else code


def fetch_nbs_series(indicator_ids, dts='199001MM-209912MM'):
    """调用新版数据接口，返回 {indicator_id: {'YYYY-MM': float}}"""
    payload = {
        'cid': CID_INDUSTRY,
        'indicatorIds': indicator_ids,
        'das': [{'text': '全国', 'value': '000000000000'}],
        'dts': [dts],
        'showType': '1',
        'rootId': NBS_ROOT_MONTHLY,
    }
    # 新版数据端点（2026-06 起为 /stream/esData，旧的 /getEsDataByCidAndDt 作兜底）
    last_err = None
    for ep in ['/stream/esData', '/getEsDataByCidAndDt']:
        try:
            r = requests.post(NBS_BASE + ep, json=payload,
                              headers={**NBS_HEADERS, 'Content-Type': 'application/json'},
                              timeout=40, verify=False)
            j = r.json()
            if j.get('success'):
                out = {iid: {} for iid in indicator_ids}
                for row in j.get('data', []):
                    key = _code_to_key(row['code'])
                    for v in row.get('values', []):
                        iid = v.get('_id')
                        val = v.get('value')
                        if iid in out and val not in ('', None):
                            try:
                                out[iid][key] = float(val)
                            except ValueError:
                                pass
                return out
        except Exception as e:
            last_err = e
    raise RuntimeError(f"NBS 数据接口调用失败: {last_err}")


def build_series():
    """构建营收、存货全量历史序列"""
    print("[1] 从国家统计局数据库拉取全量历史...", flush=True)
    data = fetch_nbs_series([IND_REVENUE_NEW, IND_REVENUE_OLD, IND_INVENTORY])
    rev_new = data[IND_REVENUE_NEW]   # 2019-02 起
    rev_old = data[IND_REVENUE_OLD]   # ~2018-12 止
    inventory = data[IND_INVENTORY]

    # 拼接营收：2018-12 及以前用"主营业务收入"，2019-01 起用"营业收入"
    revenue = OrderedDict()
    for k in sorted(rev_old.keys()):
        if k <= '2018-12':
            revenue[k] = rev_old[k]
    for k in sorted(rev_new.keys()):
        if k >= '2019-01':
            revenue[k] = rev_new[k]
    revenue = OrderedDict(sorted(revenue.items()))
    inventory = OrderedDict(sorted(inventory.items()))

    print(f"  营收: {len(revenue)} 点 ({next(iter(revenue))} ~ {list(revenue)[-1]})", flush=True)
    print(f"  存货: {len(inventory)} 点 ({next(iter(inventory))} ~ {list(inventory)[-1]})", flush=True)
    return revenue, inventory


def collect_source_urls(max_pages=12):
    """轻量抓取最新发布页，收集'规模以上工业企业利润'原文链接 -> {YYYY-MM: url}"""
    urls = OrderedDict()
    for page in range(0, max_pages):
        url = ZXFB_BASE + (f"index_{page}.html" if page > 0 else "index.html")
        try:
            r = requests.get(url, headers=ZXFB_HEADERS, timeout=15, verify=False)
            r.encoding = 'utf-8'
            if r.status_code != 200:
                break
        except Exception:
            break
        for m in re.finditer(r'<a\s[^>]*href="(\./[^"\.]+\.html)"[^>]*>([^<]*规[模上工业企利润][^<]*)</a>', r.text):
            href, title = m.group(1), m.group(2).strip()
            if '规模以上工业企业利润' not in title:
                continue
            dm = re.search(r'(\d{4})年\D*(\d{1,2})[—–\-](\d{1,2})?月?', title)
            if not dm:
                continue
            end_m = dm.group(3) or dm.group(2)
            key = f"{dm.group(1)}-{int(end_m):02d}"
            urls.setdefault(key, urljoin(ZXFB_BASE, href))
        time.sleep(0.2)
    return urls


def main():
    print("=" * 60, flush=True)
    print("规模以上工业企业数据采集（收录全部可得历史）", flush=True)
    print("=" * 60, flush=True)

    base = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base, "results", "industry_data.json")

    # 保留已有的 source_urls（历史原文链接）
    source_urls = OrderedDict()
    if os.path.exists(json_path):
        try:
            with open(json_path, encoding='utf-8') as f:
                old = json.load(f)
            source_urls.update(old.get('source_urls', {}))
        except Exception:
            pass

    # 1. 全量历史数据
    revenue, inventory = build_series()

    # 2. 补充最新发布原文链接
    print("\n[2] 抓取最新发布原文链接...", flush=True)
    try:
        new_urls = collect_source_urls()
        source_urls.update(new_urls)
        print(f"  原文链接: 共 {len(source_urls)} 条（新增/更新 {len(new_urls)}）", flush=True)
    except Exception as e:
        print(f"  跳过（{e}）", flush=True)
    source_urls = OrderedDict(sorted(source_urls.items()))

    # 3. 生成 JSON
    result = {
        "data_type": "规模以上工业企业",
        "generated_at": __import__('datetime').datetime.now().isoformat(),
        "data_source": "国家统计局",
        "notes": "营业收入累计同比：2018-12 及以前为'主营业务收入累计增长'，2019 年起为'营业收入累计增长'；"
                 "存货为'产成品存货增减'。规模以上工业企业统计口径历年有调整（2011 年起标准为年主营业务收入 2000 万元及以上），增速按可比口径计算。",
        "revenue_yoy": dict(revenue),
        "inventory_yoy": dict(inventory),
        "source_urls": dict(source_urls),
    }

    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] 已保存: {json_path}", flush=True)
    print(f"   营收数据点: {len(revenue)}  ({next(iter(revenue))} ~ {list(revenue)[-1]})", flush=True)
    print(f"   存货数据点: {len(inventory)}  ({next(iter(inventory))} ~ {list(inventory)[-1]})", flush=True)


if __name__ == "__main__":
    main()
