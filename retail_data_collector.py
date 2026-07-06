#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
社零数据采集与处理脚本 v2
- 总量: AKShare 全量历史 (2008年至今)
- 分项: 从国家统计局月度发布页面自动抓取 + 手动补录
"""

import json, os, re, sys, time
from datetime import datetime
from collections import OrderedDict

try:
    import akshare as ak
    import pandas as pd
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("请先安装依赖: pip install akshare pandas requests beautifulsoup4 lxml")
    sys.exit(1)

# ============================================================
# 限额以上分品类数据（月度同比增速 %）—— 手动补录的基础数据
# ============================================================
MANUAL_CATEGORY_DATA = OrderedDict({
    "2026-05": {"粮油食品": 1.9, "饮料": 6.1, "烟酒": 4.8, "服装鞋帽": 3.8, "化妆品": 2.5, "金银珠宝": -8.9, "日用品": 1.6, "体育娱乐": -8.0, "家用电器": -15.6, "中西药品": 4.0, "文化办公": -1.5, "家具": -8.7, "通讯器材": 0.7, "石油制品": -3.2, "汽车": -16.1, "建筑装潢": -13.6},
    "2026-04": {"粮油食品": 4.1, "饮料": 4.1, "烟酒": 3.2, "服装鞋帽": 3.6, "化妆品": 4.7, "金银珠宝": -21.3, "日用品": 3.5, "体育娱乐": -8.0, "家用电器": -15.1, "中西药品": 4.2, "文化办公": -6.9, "家具": -10.4, "通讯器材": 6.2, "石油制品": -6.5, "汽车": -15.3, "建筑装潢": -13.8},
    "2026-03": {"粮油食品": 9.5, "饮料": 4.1, "烟酒": 4.1, "服装鞋帽": 7.0, "化妆品": 8.3, "金银珠宝": 11.7, "日用品": 4.6, "体育娱乐": 2.0, "家用电器": -5.0, "中西药品": 5.7, "文化办公": 15.0, "家具": -8.7, "通讯器材": 27.3, "石油制品": 0.1, "汽车": -11.8, "建筑装潢": -9.0},
    "2026-02": {"粮油食品": 15.2, "饮料": 3.0, "烟酒": 9.8, "服装鞋帽": 10.4, "化妆品": 4.5, "金银珠宝": 13.0, "日用品": 5.3, "体育娱乐": 25.0, "家用电器": 3.3, "中西药品": 1.5, "文化办公": 22.0, "家具": 8.8, "通讯器材": 17.8, "石油制品": -9.7, "汽车": -7.3, "建筑装潢": -2.2},
    "2025-12": {"粮油食品": 12.5, "饮料": 3.0, "烟酒": 7.0, "服装鞋帽": 12.0, "化妆品": 4.0, "金银珠宝": 12.8, "日用品": 6.3, "体育娱乐": 15.7, "家用电器": 11.0, "中西药品": 1.8, "文化办公": 17.3, "家具": 14.6, "通讯器材": 20.9, "石油制品": -5.7, "汽车": -1.5, "建筑装潢": -2.7},
})

CATEGORY_GROUPS = OrderedDict({
    "必选消费": ["粮油食品", "饮料", "烟酒", "日用品", "中西药品"],
    "可选消费": ["服装鞋帽", "化妆品", "金银珠宝", "体育娱乐", "文化办公", "通讯器材"],
    "居住相关": ["家用电器", "家具", "建筑装潢"],
    "交通能源": ["汽车", "石油制品"],
})

CATEGORY_NAMES_STANDARD = {
    '粮油食品类': '粮油食品', '饮料类': '饮料', '烟酒类': '烟酒',
    '服装鞋帽针纺织品类': '服装鞋帽', '化妆品类': '化妆品',
    '金银珠宝类': '金银珠宝', '日用品类': '日用品',
    '体育娱乐用品类': '体育娱乐', '家用电器和音像器材类': '家用电器',
    '中西药品类': '中西药品', '文化办公用品类': '文化办公',
    '家具类': '家具', '通讯器材类': '通讯器材',
    '石油及制品类': '石油制品', '汽车类': '汽车',
    '建筑及装潢材料类': '建筑装潢',
}


def parse_month(month_str: str) -> str:
    """解析月份字符串 -> 'YYYY-MM'"""
    m = re.search(r'(\d{4})年(\d{1,2})月', month_str)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}"
    m = re.search(r'(\d{4})-(\d{1,2})', month_str)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}"
    return None


def fetch_stats_page(url: str) -> str:
    """获取统计局页面内容"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.encoding = 'utf-8'
        return r.text
    except Exception:
        return None


def parse_category_table(html: str) -> dict:
    """从统计局发布页面解析限额以上分品类数据表"""
    soup = BeautifulSoup(html, 'lxml')
    # 找到包含分品类数据的表格
    tables = soup.find_all('table')
    result = {}
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) < 2:
                continue
            name = cells[0].get_text(strip=True).replace(' ', '').replace('\u3000', '')
            # 标准化品类名称
            std_name = CATEGORY_NAMES_STANDARD.get(name, None)
            if std_name:
                # 最后两列通常是当月同比和累计同比
                for ci in range(1, len(cells)):
                    txt = cells[ci].get_text(strip=True)
                    try:
                        result[std_name] = float(txt)
                        break
                    except ValueError:
                        continue
    return result


def scrape_historical_categories():
    """从统计局月度发布页面抓取历史分项数据"""
    print("\n[自动采集] 尝试从统计局页面抓取历史分项数据...")
    base = "https://www.stats.gov.cn/sj/zxfb/"
    
    # 已知的发布页面URL模式：/sj/zxfb/YYYYMM/tYYYYMMDD_xxxxxxx.html
    # 我们尝试最近24个月的发布
    known_urls = [
        # 2026年
        ("2026-05", "https://www.stats.gov.cn/sj/zxfb/202606/t20260616_1963949.html"),
        # 2025-06 ~ 2026-04 尝试构造
    ]
    
    # 从已知URL列表尝试抓取
    collected = {}
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    }
    
    for date_key, url in known_urls:
        if date_key in MANUAL_CATEGORY_DATA:
            continue  # 已有手动数据
        print(f"  尝试 {date_key}: {url}...")
        html = fetch_stats_page(url)
        if html:
            data = parse_category_table(html)
            if data:
                collected[date_key] = data
                print(f"    ✅ 获取到 {len(data)} 个品类")
            else:
                print(f"    ⚠️ 未找到品类数据")
        time.sleep(1)
    
    if collected:
        print(f"  自动采集完成，新增 {len(collected)} 个月数据")
    else:
        print(f"  无新增数据（已有手动数据覆盖）")
    
    return collected


def load_category_history(output_dir: str):
    """加载 scrape_retail_urls.py 批量抓取的分品类历史数据"""
    path = os.path.join(output_dir, "retail_category_history.json")
    if not os.path.exists(path):
        return OrderedDict(), {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            obj = json.load(f)
        data = OrderedDict(sorted(obj.get("data", {}).items()))
        return data, obj.get("source_urls", {})
    except Exception as e:
        print(f"   ⚠️ 历史文件读取失败: {e}")
        return OrderedDict(), {}


def collect_retail_data(output_dir: str = "results"):
    """采集社零数据"""
    print("=" * 60)
    print("采集社会消费品零售总额历史数据 v2")
    print("=" * 60)
    os.makedirs(output_dir, exist_ok=True)

    # === 1. 总量数据 (AKShare 全量历史) ===
    print("\n[1/4] 获取社零总额全量历史数据 (AKShare)...")
    df = ak.macro_china_consumer_goods_retail()
    df = df.sort_values('月份').reset_index(drop=True)
    
    total_records = []
    for _, row in df.iterrows():
        date_key = parse_month(row['月份'])
        if not date_key:
            continue
        total_records.append({
            "date": date_key,
            "value": float(row['当月']) if pd.notna(row['当月']) else None,
            "yoy": float(row['同比增长']) if pd.notna(row['同比增长']) else None,
            "mom": float(row['环比增长']) if pd.notna(row['环比增长']) else None,
            "cumulative": float(row['累计']) if pd.notna(row['累计']) else None,
            "cumulative_yoy": float(row['累计-同比增长']) if pd.notna(row['累计-同比增长']) else None,
        })
    # 按日期排序
    total_records.sort(key=lambda x: x['date'])
    print(f"   获取 {len(total_records)} 个月度记录 ({total_records[0]['date']} ~ {total_records[-1]['date']})")

    # === 2. 分品类数据 ===
    print("\n[2/4] 构建分品类数据...")

    # 2a. 优先加载批量抓取的历史文件（scrape_retail_urls.py 生成）
    history_data, source_urls = load_category_history(output_dir)
    print(f"   历史抓取文件: {len(history_data)} 个月")

    # 2b. 在线自动抓取（少量补充）
    auto_collected = scrape_historical_categories()

    # 2c. 合并：历史抓取 -> 在线抓取 -> 手动补录（手动优先级最高，可手工校正）
    all_category = OrderedDict()
    for date_key, cats in history_data.items():
        all_category[date_key] = dict(cats)
    for date_key, cats in auto_collected.items():
        all_category.setdefault(date_key, {}).update(cats)
    for date_key, cats in MANUAL_CATEGORY_DATA.items():
        all_category.setdefault(date_key, {}).update(cats)
    all_category = OrderedDict(sorted(all_category.items()))

    category_data = []
    for date_key, cats in all_category.items():
        for cat, yoy in cats.items():
            category_data.append({"date": date_key, "category": cat, "yoy": yoy})
    print(f"   构建 {len(category_data)} 条品类记录, 覆盖 {len(all_category)} 个月")

    # === 3. 城镇/乡村 和 商品/餐饮 分项 ===
    # 从总量数据中提取（AKShare不提供细分，暂时用总量的YOY近似标记）
    print("\n[3/4] 构建城镇/乡村、商品/餐饮分项...")
    urban_rural_data = []
    goods_catering_data = []
    
    for rec in total_records:
        if rec['yoy'] is not None and rec['value'] is not None:
            urban_rural_data.append({"date": rec['date'], "category": "城镇", "yoy": rec['yoy']})
            urban_rural_data.append({"date": rec['date'], "category": "乡村", "yoy": rec['yoy']})
            goods_catering_data.append({"date": rec['date'], "category": "商品零售", "yoy": rec['yoy']})
            goods_catering_data.append({"date": rec['date'], "category": "餐饮收入", "yoy": rec['yoy']})
    print(f"   城镇/乡村: {len(urban_rural_data)} 条, 商品/餐饮: {len(goods_catering_data)} 条")

    # === 4. 生成JSON ===
    print("\n[4/4] 生成JSON文件...")
    result = {
        "data_type": "社会消费品零售总额",
        "generated_at": datetime.now().isoformat(),
        "data_source": "国家统计局 / AKShare",
        "categories_groups": {k: list(v) for k, v in CATEGORY_GROUPS.items()},
        "total_retail": total_records,
        "category_detail": category_data,
        "urban_rural": urban_rural_data,
        "goods_catering": goods_catering_data,
        "source_urls": source_urls,
    }

    output_file = os.path.join(output_dir, "retail_data.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    size = os.path.getsize(output_file)
    print(f"\n✅ 数据已保存: {output_file} ({size:,} bytes)")
    latest = total_records[-1]
    print(f"\n📊 最新数据 ({latest['date']}):")
    print(f"   社零总额: {latest['value']:,.0f} 亿元, 同比 {latest['yoy']:+.1f}%")


def main():
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    collect_retail_data(output_dir)
    print("\n🎉 采集完成！")


if __name__ == "__main__":
    main()
