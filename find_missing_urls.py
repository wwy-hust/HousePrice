#!/usr/bin/env python3
"""批量搜索统计局社零每月发布URL，补齐缺失月份"""
import requests, re, time, json, io, pandas as pd
from urllib.parse import urljoin
from collections import OrderedDict

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Referer': 'https://www.stats.gov.cn/sj/zxfb/',
}

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

# 已知URL（含ID范围）
known_ids = [
    (1901406, '2022-02'), (1901464, '2022-04'), (1901490, '2022-05'),
    (1937198, '2023-02'), (1945604, '2023-11'), (1946619, '2023-12'),
    (1948175, '2024-02'), (1955609, '2024-06'), (1957759, '2024-11'),
    (1959014, '2025-02'), (1962786, '2026-02'), (1963727, '2026-04'),
    (1963949, '2026-05'),
]

# 从已知ID猜测附近ID对应的URL目录
# 每个ID对应一个目录YYYYMM（从URL路径提取）
id_to_dir = {
    1901406: '202302',  # 2022-02数据，2023-02发布
    1901464: '202302',
    1901490: '202302',
    1937198: '202303',
    1945604: '202312',
    1946619: '202401',
    1948175: '202403',
    1955609: '202407',
    1957759: '202412',
    1959014: '202503',
    1962786: '202603',
    1963727: '202605',
    1963949: '202606',
}

# 推断：每个ID之间可能有哪些？
# 扫描ID范围，构造URL检查
def scan_ids():
    """扫描已知ID附近查找更多URL"""
    found = OrderedDict()
    # 扫描每个已知ID ±100 范围
    for base_id, dk in known_ids:
        pub_dir = id_to_dir[base_id]
        for delta in range(-100, 101):
            test_id = base_id + delta
            if test_id < 1900000 or test_id > 1970000:
                continue
            # 构造URL（用发布月目录）
            url = f'https://www.stats.gov.cn/sj/zxfb/{pub_dir}/t{pub_dir}16_{test_id}.html'
            try:
                r = requests.head(url, headers=HEADERS, timeout=5)
                if r.status_code == 200:
                    # 确认是社零发布页
                    r2 = requests.get(url, headers=HEADERS, timeout=10)
                    r2.encoding = 'utf-8'
                    if '社会消费品零售总额' in r2.text and '限额以上' in r2.text:
                        # 提取月份
                        dm = re.search(r'(\d{4})年(\d{1,2})[——–\-](\d{1,2})月', r2.text[:2000])
                        if dm:
                            key = f"{dm.group(1)}-{int(dm.group(3)):02d}"
                            if key not in found:
                                found[key] = url
                                print(f'  发现: {key} -> {url}', flush=True)
            except:
                pass
            time.sleep(0.05)  # 少量延迟避免被封
        print(f'  ID {base_id}±100 扫描完成, 累计 {len(found)}' , flush=True)
    return found

if __name__ == '__main__':
    print('扫描已知ID附近URL...')
    found = scan_ids()
    print(f'\n总计新增: {len(found)}')
    for k in sorted(found.keys()):
        print(f'  {k} -> {found[k]}')
