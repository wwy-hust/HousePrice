#!/usr/bin/env python3
"""直接拉取关注资产价格并导出为 HousePrice 可读取的 JSON。"""

from __future__ import annotations

import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import median
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


HOUSE_PRICE_ROOT = Path(__file__).resolve().parent
OUTPUT_PATH = HOUSE_PRICE_ROOT / "results" / "asset_price_data.json"
REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0 (HousePrice asset collector)"}
MAX_HISTORY_DAYS = 3650
SULFUR_RECENT_CHART_URL = (
    "https://www.100ppi.com/graph/cindex.php?f=graph_ppid_ave&ppid=427"
)
SULFUR_HISTORY_URL = "https://www.100ppi.com/cindex/?f=n_graph&ppid=427"
SULFUR_DETAIL_URL = "https://www.100ppi.com/rawmex/detail-427.html"
PYRITE_LIST_URL = "https://www.100ppi.com/mprice/plist-1-561-{page}.html"
PHOSPHATE_ROCK_HISTORY_URL = (
    "https://www.mysteel.com/oilchem/article/nwj1r6/"
)
DYE_REDUCTION_EARLY_URL = (
    "https://news.chemnet.com/toutiao/detail-53508.html"
)
DYE_REDUCTION_FEBRUARY_URL = (
    "https://www.100ppi.com/forecast/detail-20260211-202306.html"
)
DYE_REDUCTION_LATEST_URL = (
    "https://news.chemnet.com/toutiao/detail-75363.html"
)
BLOOD_PRODUCT_PRICE_URL = (
    "http://www.gaoqing.gov.cn/gongkai/site_gqxwsjkj/"
    "channel_6305cf96328b0c0108580897/doc_683919151427114bd64b539d.html"
)
FEEDTRADE_LIST_URL = "https://www.feedtrade.com.cn/additive/vitamin/index.html"
XINDE_API_ROOT = "https://www.xindemarinenews.com.cn/jeecgboot/xinde"
CCGP_SEARCH_URL = "https://search.ccgp.gov.cn/bxsearch"
SMM_API_URL = "https://platform.smm.cn/aggdatacenter/user/v1/agg_data"
SMM_ASSETS = {
    "SB_CN": {
        "product_id": "201309290001",
        "name": "锑锭（国内，2#低铋）",
        "source_url": "https://hq.smm.cn/h5/antimony-price",
    },
    "SB_INTL": {
        "product_id": "202511250003",
        "name": "锑锭（国外，欧洲交货）",
        "source_url": "https://hq.smm.cn/h5/antimony-price",
    },
    "W_CN": {
        "product_id": "201308090018",
        "name": "仲钨酸铵（国内）",
        "source_url": "https://hq.smm.cn/tungsten/category/201308090018",
    },
    "W_INTL": {
        "product_id": "202511260001",
        "name": "仲钨酸铵（国外，鹿特丹CIF）",
        "source_url": "https://hq.smm.cn/tungsten/category/202511260001",
    },
}
SMM_ALUMINA_ASSETS = {
    "ALUMINA": {
        "product_id": "201106140030",
        "name": "氧化铝（SMM全国加权指数）",
        "source_url": "https://hq.smm.cn/h5/SMM-alumina-price",
    },
}
SMM_ALUMINUM_ASSETS = {
    "ALUMINUM": {
        "product_id": "201102250311",
        "name": "电解铝（SMM A00铝）",
        "source_url": "https://hq.smm.cn/aluminum/category/201102250311",
    },
}

REFERENCE_POINTS = {
    "PYRITE": [
        {
            "date": "2022-07-31",
            "price": 450.0,
            "price_low": 450.0,
            "price_high": 450.0,
            "source_url": "https://www.100ppi.com/news/detail-20220731-2221680.html",
            "date_precision": "day",
            "date_label": "2022-07-31",
            "quote_type": "supplier_offer",
            "quality_note": "生意社历史报价报道，属于供应商报价，并非连续市场指数。",
            "comparability_note": "国产硫化铁含量45%-47%，与当前规格一致。",
        },
    ],
    "PHOSPHATE_ROCK": [
        {
            "date": "2016-06-09",
            "price": 340.0,
            "price_low": None,
            "price_high": None,
            "source_url": "http://www.cnfert.com/ylgy/2016-06-09/72744.html",
            "date_precision": "day",
            "date_label": "2016-06-09",
            "quote_type": "supplier_offer",
            "quality_note": "行业报道中的企业报价，仅作为历史参考点，并非连续行情。",
            "comparability_note": (
                "同为四川马边30%磷精矿县城交货价，但报价企业为马边南方矿业，"
                "当前主序列为马边瑞丰矿业，税费口径也可能不同。"
            ),
        },
        {
            "date": "2016-07-07",
            "price": 340.0,
            "price_low": None,
            "price_high": None,
            "source_url": "http://www.cnfert.com/ylgy/2016-07-07/73804.html",
            "date_precision": "day",
            "date_label": "2016-07-07",
            "quote_type": "supplier_offer",
            "quality_note": "行业报道中的企业报价，仅作为历史参考点，并非连续行情。",
            "comparability_note": (
                "同为四川马边30%磷矿石，但报价企业为马边南方矿业，"
                "当前主序列为马边瑞丰矿业，交货和税费口径可能不同。"
            ),
        },
    ],
    "DYE_REDUCTION": [
        {
            "date": "2016-06-30",
            "price": 33000,
            "price_low": None,
            "price_high": None,
            "source_url": "https://www.chyxx.com/industry/201608/437750.html",
            "date_precision": "half_year",
            "date_label": "2016年上半年",
            "quote_type": "reported_market_price",
            "quality_note": "行业分析报道中的阶段价格，仅作为历史参考点，并非精确日价。",
            "comparability_note": "报道明确指向分散染料还原物。",
        },
        {
            "date": "2019-04-30",
            "price": 118000,
            "price_low": None,
            "price_high": None,
            "source_url": "https://consult.pharnexcloud.com/report/detail/114627.html",
            "date_precision": "event",
            "date_label": "2019年响水事件后",
            "quote_type": "reported_historical_high",
            "quality_note": "后续证券研报转述百川盈孚历史高点，仅作事件参考。",
            "comparability_note": "报道指向还原物历史高点，但未披露精确交易日期。",
        },
        {
            "date": "2020-01-31",
            "price": 40000,
            "price_low": None,
            "price_high": None,
            "source_url": "https://j.eastday.com/m/1583241305010611",
            "date_precision": "month",
            "date_label": "2020年春节前",
            "quote_type": "reported_market_price",
            "quality_note": "新闻报道中的阶段价格，仅作为历史参考点，并非精确日价。",
            "comparability_note": "报道明确指向分散染料还原物。",
        },
        {
            "date": "2020-03-01",
            "price": 100000,
            "price_low": None,
            "price_high": None,
            "source_url": "https://j.eastday.com/m/1583241305010611",
            "date_precision": "month",
            "date_label": "2020年3月初",
            "quote_type": "reported_market_price",
            "quality_note": "新闻报道称价格超过10万元/吨，图中按10万元记录下限参考。",
            "comparability_note": "报道明确指向分散染料还原物。",
        },
        {
            "date": "2021-01-01",
            "price": 42000,
            "price_low": None,
            "price_high": None,
            "source_url": "https://www.jjchem.net/news/202103/03227038.html",
            "date_precision": "month",
            "date_label": "2021年1月",
            "quote_type": "reported_offer",
            "quality_note": "中国化工报转载中的含税报价，仅作为历史参考点。",
            "comparability_note": "还原物含税报价，不等同于统一市场成交指数。",
        },
        {
            "date": "2021-03-15",
            "price": 48000,
            "price_low": None,
            "price_high": None,
            "source_url": "https://www.jjchem.net/news/202103/03227038.html",
            "date_precision": "half_month",
            "date_label": "2021年3月中旬",
            "quote_type": "reported_offer",
            "quality_note": "中国化工报转载中的含税报价，仅作为历史参考点。",
            "comparability_note": "还原物含税报价，不等同于统一市场成交指数。",
        },
        {
            "date": "2025-12-31",
            "price": 25000,
            "price_low": None,
            "price_high": None,
            "source_url": DYE_REDUCTION_EARLY_URL,
            "date_precision": "year",
            "date_label": "2025年低位/年末",
            "quote_type": "reported_market_price",
            "quality_note": "报道对年内低位的回顾，仅作为历史参考点，并非精确日价。",
            "comparability_note": "报道明确指向分散染料还原物。",
        },
        {
            "date": "2026-02-11",
            "price": 70000,
            "price_low": None,
            "price_high": None,
            "source_url": DYE_REDUCTION_FEBRUARY_URL,
            "date_precision": "day",
            "date_label": "2026-02-11",
            "quote_type": "reported_market_price",
            "quality_note": "生意社行情报道中的市场价格，并非连续报价序列。",
            "comparability_note": "报道明确指向分散染料还原物。",
        },
        {
            "date": "2026-03-05",
            "price": 100000,
            "price_low": None,
            "price_high": None,
            "source_url": DYE_REDUCTION_EARLY_URL,
            "date_precision": "day",
            "date_label": "2026-03-05",
            "quote_type": "reported_market_price",
            "quality_note": "行业报道中的市场价格，并非连续报价序列。",
            "comparability_note": "报道明确指向分散染料还原物。",
        },
        {
            "date": "2026-07-21",
            "price": 120000,
            "price_low": None,
            "price_high": None,
            "source_url": DYE_REDUCTION_LATEST_URL,
            "date_precision": "day",
            "date_label": "2026-07-21",
            "quote_type": "reported_offer",
            "quality_note": "企业调价函报道中的报价，并非市场成交价或连续指数。",
            "comparability_note": "报道明确指向分散染料还原物。",
        },
    ],
    "VD3": [
        {
            "date": point_date,
            "price": price,
            "price_low": None,
            "price_high": None,
            "source_url": (
                "https://pdf.dfcfw.com/pdf/H3_AP202408051639134632_1.pdf"
                "?1722851414000.pdf="
            ),
            "date_precision": "day",
            "date_label": point_date,
            "quote_type": "secondary_market_series",
            "quality_note": "证券研究报告引用iFinD的历史节点，仅作为二手报道参考。",
            "comparability_note": "中国饲料级维生素D3价格，报告未逐点披露具体品牌。",
        }
        for point_date, price in (
            ("2016-03-01", 66.5),
            ("2016-03-28", 187.5),
            ("2017-05-31", 67.5),
            ("2017-06-23", 425.0),
            ("2018-06-04", 260.0),
            ("2018-06-28", 625.0),
            ("2020-02-10", 97.5),
            ("2020-04-22", 360.0),
            ("2024-05-23", 56.5),
            ("2024-07-24", 255.0),
        )
    ],
    "BLOOD_ALBUMIN": [
        {
            "date": "2022-05-30",
            "price": 377.5,
            "price_low": 350.0,
            "price_high": 520.0,
            "source_url": "https://pdf.dfcfw.com/pdf/H3_AP202205301568831998_1.pdf",
            "date_precision": "event",
            "date_label": "2022年广东联盟集采",
            "quote_type": "alliance_procurement_sample_median",
            "quality_note": "证券研报整理的广东联盟集采样本中位数，仅作历史参考。",
            "comparability_note": "固定为10g（20%×50ml），包含不同生产企业。",
            "sample_count": 8,
        },
        {
            "date": "2025-07-24",
            "price": 369.0,
            "price_low": 369.0,
            "price_high": 369.0,
            "source_url": (
                "https://ybj.qinghai.gov.cn/20250724/"
                "403ef4788db14e1bb386bfa5bcb82df0/"
                "20250724403ef4788db14e1bb386bfa5bcb82df0_"
                "35a4c60ee98b904b6ab36084526b6dae92.pdf"
            ),
            "date_precision": "day",
            "date_label": "2025-07-24",
            "quote_type": "official_listed_price",
            "quality_note": "青海医保局价格调整表中的公开挂网价。",
            "comparability_note": "国产人血白蛋白10g/瓶（20%，50ml），单一企业样本。",
            "sample_count": 1,
        },
    ],
    "BLOOD_IVIG": [
        {
            "date": "2020-12-31",
            "price": 590.86,
            "price_low": 541.0,
            "price_high": 620.0,
            "source_url": "https://www.chyxx.com/industry/202102/929959.html",
            "date_precision": "year",
            "date_label": "2020年公开中标样本均价",
            "quote_type": "reported_bid_average",
            "quality_note": "智研咨询汇总的公开竞价样本年度均价，仅作历史参考。",
            "comparability_note": "静丙2.5g规格，不同省份和生产企业的非完整样本。",
            "sample_count": 43,
        },
        {
            "date": "2021-01-19",
            "price": 576.33,
            "price_low": 561.0,
            "price_high": 586.0,
            "source_url": "https://www.chyxx.com/industry/202102/929959.html",
            "date_precision": "day",
            "date_label": "2021-01-19公开中标样本均价",
            "quote_type": "reported_bid_average",
            "quality_note": "智研咨询汇总的3个公开中标样本均价，仅作历史参考。",
            "comparability_note": "静丙2.5g规格，贵州地区不同生产企业样本。",
            "sample_count": 3,
        },
        {
            "date": "2026-02-12",
            "price": 560.4,
            "price_low": 560.4,
            "price_high": 560.4,
            "source_url": (
                "http://ybj.qinghai.gov.cn/20260212/"
                "5301c294485341d784e8aa9aa4521b1b/"
                "202602125301c294485341d784e8aa9aa4521b1b_"
                "18f0156694617447c8824bc6b1d94bbd1a.pdf"
            ),
            "date_precision": "day",
            "date_label": "2026-02-12",
            "quote_type": "official_listed_price",
            "quality_note": "青海医保局广东联盟接续中选药品挂网价。",
            "comparability_note": "静丙2.5g/瓶（5%，50ml），单一企业样本。",
            "sample_count": 1,
        },
    ],
}

DEFAULT_VISIBLE_REFERENCE_DATES = {
    "DYE_REDUCTION": {
        "2025-12-31",
        "2026-02-11",
        "2026-03-05",
        "2026-07-21",
    },
    "BLOOD_ALBUMIN": {"2025-07-24"},
    "BLOOD_IVIG": {"2026-02-12"},
}

for code, reference_points in REFERENCE_POINTS.items():
    visible_dates = DEFAULT_VISIBLE_REFERENCE_DATES.get(code, set())
    for reference_point in reference_points:
        reference_point["point_type"] = (
            "reported_observation"
            if reference_point["date"] in visible_dates
            else "reported_reference"
        )
        reference_point["default_hidden"] = (
            reference_point["date"] not in visible_dates
        )

CATEGORY_BY_CODE = {
    "SULFUR": "大宗商品",
    "PYRITE": "大宗商品",
    "ALUMINA": "大宗商品",
    "ALUMINUM": "大宗商品",
    "PHOSPHATE_ROCK": "大宗商品",
    "DYE_REDUCTION": "化工中间体",
    "SB_CN": "小金属",
    "SB_INTL": "小金属",
    "W_CN": "小金属",
    "W_INTL": "小金属",
    "VD3": "饲料添加剂",
    "BLOOD_ALBUMIN": "血液制品",
    "BLOOD_IVIG": "血液制品",
    "TD3C": "VLCC油运",
    "TD3C_WS": "VLCC油运",
    "TD15": "VLCC油运",
    "TD15_WS": "VLCC油运",
    "MONKEY": "生物医药上游",
}
CATEGORY_ORDER = [
    "大宗商品",
    "化工中间体",
    "小金属",
    "饲料添加剂",
    "VLCC油运",
    "血液制品",
    "生物医药上游",
]
ASSET_ORDER = {
    "SULFUR": 0,
    "PYRITE": 1,
    "ALUMINA": 2,
    "ALUMINUM": 3,
    "PHOSPHATE_ROCK": 4,
    "BLOOD_ALBUMIN": 0,
    "BLOOD_IVIG": 1,
}


def _get_smm_data(endpoint: str, params: dict[str, str]) -> list[dict]:
    response = requests.get(
        f"{SMM_API_URL}/{endpoint}",
        params=params,
        headers={
            "User-Agent": "HousePrice/1.0",
            "Referer": "https://hq.smm.cn/",
        },
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") != 0 or not isinstance(payload.get("data"), list):
        raise RuntimeError(f"上海有色网接口返回异常：{payload.get('msg', '未知错误')}")
    return payload["data"]


def _fetch_smm_assets(
    configs: dict[str, dict[str, str]],
    category: str,
    history_days: int = MAX_HISTORY_DAYS,
) -> list[dict]:
    """拉取一组 SMM 价格，并转换为前端通用资产结构。"""
    product_ids = ",".join(
        config["product_id"] for config in configs.values()
    )
    today = date.today()
    history_start = today - timedelta(days=history_days)
    history_by_id: dict[str, dict] = {}
    window_start = history_start
    while window_start <= today:
        window_end = min(window_start + timedelta(days=1094), today)
        params = {
            "product_ids": product_ids,
            "begin_date": window_start.isoformat(),
            "end_date": window_end.isoformat(),
        }
        for item in _get_smm_data("history_price", params):
            product_id = item["product_id"]
            accumulated = history_by_id.setdefault(
                product_id,
                {**item, "price_detail": []},
            )
            accumulated["price_detail"].extend(item.get("price_detail", []))
        window_start = window_end + timedelta(days=1)
    latest_by_id = {
        item["product_id"]: item
        for item in _get_smm_data("latest_price", {"product_ids": product_ids})
    }

    assets = []
    for code, config in configs.items():
        product_id = config["product_id"]
        history = history_by_id.get(product_id)
        latest = latest_by_id.get(product_id)
        if not history or not latest:
            raise RuntimeError(f"上海有色网未返回 {config['name']} 数据")

        points_by_date = {
            point["renew_date"]: {
                "date": point["renew_date"],
                "price": point["average"],
                "price_low": None,
                "price_high": None,
                "source_url": config["source_url"],
            }
            for point in history.get("price_detail", [])
            if point.get("renew_date") and point.get("average") is not None
        }
        latest_date = latest["renew_date"]
        points_by_date[latest_date] = {
            "date": latest_date,
            "price": latest["average"],
            "price_low": latest.get("low"),
            "price_high": latest.get("high"),
            "source_url": config["source_url"],
        }
        series = [points_by_date[key] for key in sorted(points_by_date)]
        assets.append(
            {
                "code": code,
                "name": config["name"],
                "unit": latest["unit"],
                "source": "上海有色网（SMM）",
                "category": category,
                "latest": series[-1],
                "series": series,
            }
        )
    return assets


def fetch_small_metal_assets(history_days: int = MAX_HISTORY_DAYS) -> list[dict]:
    """拉取国内和国外小金属价格，并转换为前端通用资产结构。"""
    return _fetch_smm_assets(SMM_ASSETS, "小金属", history_days)


def fetch_alumina_asset(history_days: int = MAX_HISTORY_DAYS) -> dict:
    """拉取 SMM 氧化铝全国加权指数。"""
    return _fetch_smm_assets(
        SMM_ALUMINA_ASSETS,
        "大宗商品",
        history_days,
    )[0]


def fetch_aluminum_asset(history_days: int = MAX_HISTORY_DAYS) -> dict:
    """拉取 SMM A00 电解铝仓库自提指导价。"""
    return _fetch_smm_assets(
        SMM_ALUMINUM_ASSETS,
        "大宗商品",
        history_days,
    )[0]


def fetch_antimony_assets(history_days: int = MAX_HISTORY_DAYS) -> list[dict]:
    """兼容旧调用，仅返回锑价。"""
    return [
        asset
        for asset in fetch_small_metal_assets(history_days)
        if asset["code"].startswith("SB_")
    ]


def load_existing_small_metal_assets(output_path: Path = OUTPUT_PATH) -> list[dict]:
    """网络拉取失败时保留上次成功导出的小金属价格。"""
    if not output_path.exists():
        return []
    try:
        payload = json.loads(output_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return [
        asset
        for asset in payload.get("assets", [])
        if asset.get("code") in SMM_ASSETS
    ]


def _get_html(url: str, *, timeout: int = 20) -> str:
    """请求网页，并兼容生意社简单的 HW_CHECK Cookie 验证。"""
    session = requests.Session()
    response = session.get(url, headers=REQUEST_HEADERS, timeout=timeout)
    response.raise_for_status()
    if response.encoding == "ISO-8859-1":
        response.encoding = response.apparent_encoding
    cookie_match = re.search(r'var _0x2 = "([a-f0-9]+)"', response.text)
    if cookie_match:
        session.cookies.set("HW_CHECK", cookie_match.group(1))
        response = session.get(url, headers=REQUEST_HEADERS, timeout=timeout)
        response.raise_for_status()
    return response.text


def _existing_series_by_code(
    code: str,
    output_path: Path = OUTPUT_PATH,
) -> dict[str, dict]:
    """读取已落盘序列，供历史抓取器只补缺失日期。"""
    if not output_path.exists():
        return {}
    try:
        payload = json.loads(output_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    asset = next(
        (item for item in payload.get("assets", []) if item.get("code") == code),
        None,
    )
    if not asset:
        return {}
    return {
        point["date"]: point
        for point in asset.get("series", [])
        if point.get("date")
    }


def _reference_points_by_date(code: str) -> dict[str, dict]:
    """复制已核验的报道参考点，避免抓取流程修改模块级配置。"""
    return {
        point["date"]: dict(point)
        for point in REFERENCE_POINTS.get(code, [])
    }


def _base62(value: int) -> str:
    alphabet = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    encoded = ""
    while True:
        encoded = alphabet[value % 62] + encoded
        value //= 62
        if value == 0:
            return encoded


def _unpack_packer(source: str) -> str:
    """解包生意社图表页面使用的 Dean Edwards P.A.C.K.E.R. 脚本。"""
    match = re.search(
        r"eval\(function\(p,a,c,k,e,d\).*?\}\("
        r"'(?P<payload>.*?)',62,(?P<count>\d+),"
        r"'(?P<keywords>.*?)'\.split\('\|'\)",
        source,
        re.DOTALL,
    )
    if not match:
        raise ValueError("未找到生意社价格图表数据")

    payload = match.group("payload")
    keywords = match.group("keywords").split("|")
    for index in range(int(match.group("count")) - 1, -1, -1):
        if index < len(keywords) and keywords[index]:
            payload = re.sub(
                rf"\b{re.escape(_base62(index))}\b",
                keywords[index],
                payload,
            )
    return payload


def fetch_sulfur_asset(history_days: int = MAX_HISTORY_DAYS) -> dict:
    """从生意社同商品年度图拉取硫磺日度历史。"""
    source = _get_html(SULFUR_HISTORY_URL)
    series_matches = re.findall(
        r"name:\s*'(?P<year>\d{4})'.*?"
        r"data:\s*\[(?P<data>.*?)\]\s*[,}]",
        source,
        re.DOTALL,
    )
    if not series_matches:
        raise ValueError("无法解析生意社硫磺年度价格序列")

    cutoff = date.today() - timedelta(days=history_days)
    points_by_date = {}
    for year_text, price_data in series_matches:
        prices = [
            float(value.strip())
            for value in price_data.split(",")
            if value.strip()
        ]
        if not prices:
            raise ValueError(f"生意社硫磺 {year_text} 年数据长度异常")
        year_start = date(int(year_text), 1, 1)
        maximum_days = (date(int(year_text) + 1, 1, 1) - year_start).days
        if len(prices) > maximum_days:
            raise ValueError(f"生意社硫磺 {year_text} 年数据长度异常")
        for day_offset, price in enumerate(prices):
            point_date = year_start + timedelta(days=day_offset)
            if point_date < cutoff:
                continue
            points_by_date[point_date.isoformat()] = {
                "date": point_date.isoformat(),
                "price": price,
                "price_low": None,
                "price_high": None,
                "source_url": SULFUR_HISTORY_URL,
            }

    recent_source = _unpack_packer(_get_html(SULFUR_RECENT_CHART_URL))
    recent_dates = re.search(
        r"xAxis:\{.*?data:\[(?P<data>.*?)\]\},yAxis:",
        recent_source,
        re.DOTALL,
    )
    recent_prices = re.search(
        r"series:\[.*?data:\[(?P<data>[\d.,\s]+)\]",
        recent_source,
        re.DOTALL,
    )
    if recent_dates and recent_prices:
        dates = re.findall(r"\d{4}-\d{2}-\d{2}", recent_dates.group("data"))
        prices = [
            float(value.replace(",", ""))
            for value in recent_prices.group("data").split(",")
            if value.strip()
        ]
        if len(dates) != len(prices):
            raise ValueError("生意社硫磺近期价格日期与数值数量不一致")
        for point_date, price in zip(dates, prices):
            if date.fromisoformat(point_date) < cutoff:
                continue
            points_by_date[point_date] = {
                "date": point_date,
                "price": price,
                "price_low": None,
                "price_high": None,
                "source_url": SULFUR_RECENT_CHART_URL,
            }
    if not points_by_date:
        raise ValueError("生意社硫磺年度图未返回指定时间范围的数据")
    series = [points_by_date[key] for key in sorted(points_by_date)]
    series[-1]["source_url"] = SULFUR_DETAIL_URL
    return {
        "code": "SULFUR",
        "name": "硫磺",
        "unit": "元/吨",
        "source": "生意社",
        "category": "大宗商品",
        "latest": series[-1],
        "series": series,
    }


def fetch_pyrite_asset(max_pages: int = 10) -> dict:
    """汇总生意社国产 45%-47% 硫铁矿的每日公开报价。"""
    prices_by_date: dict[str, list[float]] = {}
    source_urls_by_date: dict[str, str] = {}

    for page in range(1, max_pages + 1):
        page_url = PYRITE_LIST_URL.format(page=page)
        soup = BeautifulSoup(_get_html(page_url), "html.parser")
        page_row_count = 0
        for row in soup.select("table tr"):
            cells = [
                cell.get_text(" ", strip=True)
                for cell in row.find_all(["td", "th"])
            ]
            if len(cells) < 8 or cells[0] != "硫铁矿":
                continue
            price_match = re.search(r"([\d,.]+)\s*元/吨", cells[3])
            point_date = cells[7]
            if not price_match or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", point_date):
                continue
            prices_by_date.setdefault(point_date, []).append(
                _number(price_match.group(1))
            )
            source_urls_by_date[point_date] = page_url
            page_row_count += 1
        if page_row_count == 0:
            break

    if not prices_by_date:
        raise ValueError("生意社报价中心未找到硫铁矿报价")

    points_by_date = _reference_points_by_date("PYRITE")
    for point_date in sorted(prices_by_date):
        prices = prices_by_date[point_date]
        points_by_date[point_date] = {
            "date": point_date,
            "price": sum(prices) / len(prices),
            "price_low": min(prices),
            "price_high": max(prices),
            "source_url": source_urls_by_date[point_date],
        }
    series = [points_by_date[key] for key in sorted(points_by_date)]
    return {
        "code": "PYRITE",
        "name": "硫铁矿",
        "unit": "元/吨",
        "source": "生意社报价中心（国产，硫化铁含量45%-47%）",
        "category": "大宗商品",
        "latest": series[-1],
        "series": series,
    }


def fetch_phosphate_rock_asset(history_pages: int = 15) -> dict:
    """拉取隆众资讯四川马边 30% 品位磷精粉公开报价。"""
    points_by_date = _existing_series_by_code("PHOSPHATE_ROCK")
    points_by_date.update(_reference_points_by_date("PHOSPHATE_ROCK"))
    article_urls = []
    for page in range(1, history_pages + 1):
        page_url = (
            PHOSPHATE_ROCK_HISTORY_URL
            if page == 1
            else f"{PHOSPHATE_ROCK_HISTORY_URL}{page}.html?keyWord="
        )
        list_soup = BeautifulSoup(_get_html(page_url), "html.parser")
        page_urls = []
        for link in list_soup.select("a[href]"):
            title = link.get_text(" ", strip=True)
            if "磷矿石企业价格一览表" not in title:
                continue
            date_match = re.search(r"\((\d{4})(\d{2})(\d{2})", title)
            point_date = "-".join(date_match.groups()) if date_match else None
            if point_date and point_date in points_by_date:
                continue
            page_urls.append(urljoin(page_url, link["href"]))
        if not page_urls:
            if page > 10:
                break
            continue
        article_urls.extend(page_urls)

    def parse_article(article_url: str) -> tuple[str, dict] | None:
        try:
            article_soup = BeautifulSoup(_get_html(article_url), "html.parser")
        except requests.RequestException:
            return None
        title_node = article_soup.select_one('meta[name="detailTit"]')
        title = (
            title_node.get("content", "")
            if title_node
            else article_soup.get_text(" ", strip=True)
        )
        date_match = re.search(r"\((\d{4})(\d{2})(\d{2})", title)
        content_node = article_soup.select_one("#article-content, #text")
        if not date_match or not content_node:
            return None

        content = re.sub(r"\s+", "", content_node.get_text("", strip=True))
        price_match = re.search(
            r"(?:四川马边.*?30%|马边瑞丰30%磷精矿)"
            r"(?P<price>\d{3,4}(?:-\d{3,4})?)(?P=price)"
            r"(?:[-+]?\d+(?:/[-+]?\d+)?)?县城交货价",
            content,
        )
        if not price_match:
            return None
        price_text = price_match.group("price")
        price_parts = [float(value) for value in price_text.split("-")]
        price_low = min(price_parts)
        price_high = max(price_parts)
        point_date = "-".join(date_match.groups())
        return (
            point_date,
            {
                "date": point_date,
                "price": sum(price_parts) / len(price_parts),
                "price_low": price_low,
                "price_high": price_high,
                "source_url": article_url,
            },
        )

    with ThreadPoolExecutor(max_workers=6) as executor:
        for parsed in executor.map(parse_article, dict.fromkeys(article_urls)):
            if parsed:
                points_by_date[parsed[0]] = parsed[1]
    if not points_by_date:
        raise ValueError("隆众资讯未找到四川马边30%品位磷精粉报价")

    series = [points_by_date[key] for key in sorted(points_by_date)]
    return {
        "code": "PHOSPHATE_ROCK",
        "name": "磷矿石（四川马边30%磷精粉）",
        "unit": "元/吨",
        "source": "隆众资讯（我的钢铁网转载）",
        "category": "大宗商品",
        "latest": series[-1],
        "series": series,
    }


def fetch_dye_reduction_asset() -> dict:
    """拉取分散染料还原物的公开市场报价节点。"""
    early_text = BeautifulSoup(
        _get_html(DYE_REDUCTION_EARLY_URL),
        "html.parser",
    ).get_text(" ", strip=True)
    february_text = BeautifulSoup(
        _get_html(DYE_REDUCTION_FEBRUARY_URL),
        "html.parser",
    ).get_text(" ", strip=True)
    latest_text = BeautifulSoup(
        _get_html(DYE_REDUCTION_LATEST_URL),
        "html.parser",
    ).get_text(" ", strip=True)
    required_phrases = (
        (early_text, ("2025", "2.5万元/吨", "3月", "10万元")),
        (february_text, ("2月", "7万元/吨")),
        (latest_text, ("7月21日", "还原物报价12万元/吨")),
    )
    if any(
        not all(phrase in text for phrase in phrases)
        for text, phrases in required_phrases
    ):
        raise ValueError("公开报道中的分散染料还原物报价格式已变化")

    series = list(_reference_points_by_date("DYE_REDUCTION").values())
    return {
        "code": "DYE_REDUCTION",
        "name": "分散染料还原物",
        "unit": "元/吨",
        "source": "ChemNet、生意社公开精确报价（非连续序列）",
        "category": "化工中间体",
        "latest": series[-1],
        "series": series,
    }


def fetch_blood_product_assets() -> list[dict]:
    """采集固定规格白蛋白和静丙的公开挂网价格样本。"""
    soup = BeautifulSoup(_get_html(BLOOD_PRODUCT_PRICE_URL), "html.parser")
    page_text = soup.get_text(" ", strip=True)
    published_match = re.search(r"发布日期[：:]\s*(\d{4}-\d{2}-\d{2})", page_text)
    if not published_match:
        raise ValueError("血制品价格公示页缺少发布日期")
    published_date = published_match.group(1)

    samples = {
        "BLOOD_ALBUMIN": [],
        "BLOOD_IVIG": [],
    }
    for row in soup.select("tr"):
        cells = [
            cell.get_text(" ", strip=True)
            for cell in row.find_all(["td", "th"])
        ]
        if len(cells) < 5:
            continue
        name, specification = cells[0], cells[1].replace(" ", "")
        price_match = re.fullmatch(r"[\d,.]+", cells[-1])
        if not price_match:
            continue
        price = _number(price_match.group())
        if (
            "人血白蛋白" in name
            and "10g" in specification
            and "20" in specification
            and "50ml" in specification.lower()
        ):
            samples["BLOOD_ALBUMIN"].append(price)
        elif (
            "静注人免疫球蛋白" in name
            and "2.5g" in specification
            and "5" in specification
            and "50ml" in specification.lower()
        ):
            samples["BLOOD_IVIG"].append(price)

    configs = {
        "BLOOD_ALBUMIN": {
            "name": "人血白蛋白（10g/50ml公开挂网样本）",
            "specification": "10g/瓶（20%，50ml）",
        },
        "BLOOD_IVIG": {
            "name": "静丙（2.5g/50ml公开挂网样本）",
            "specification": "2.5g/瓶（5%，50ml，pH4）",
        },
    }
    assets = []
    for code, config in configs.items():
        prices = samples[code]
        if not prices:
            raise ValueError(f"价格公示页未找到{config['name']}数据")
        points_by_date = _existing_series_by_code(code)
        points_by_date.update(_reference_points_by_date(code))
        points_by_date[published_date] = {
            "date": published_date,
            "price": median(prices),
            "price_low": min(prices),
            "price_high": max(prices),
            "source_url": BLOOD_PRODUCT_PRICE_URL,
            "point_type": "reported_observation",
            "default_hidden": False,
            "date_precision": "day",
            "date_label": published_date,
            "quote_type": "public_hospital_listed_sample_median",
            "quality_note": "公立医院公开药品价格样本中位数，并非全国实际成交价。",
            "comparability_note": (
                f"统一规格为{config['specification']}，样本包含不同生产企业。"
            ),
            "sample_count": len(prices),
        }
        series = [points_by_date[key] for key in sorted(points_by_date)]
        assets.append(
            {
                "code": code,
                "name": config["name"],
                "unit": "元/瓶",
                "source": "政府及公立医院公开挂网/中标价格样本",
                "category": "血液制品",
                "latest": series[-1],
                "series": series,
            }
        )
    return assets


def _parse_price_range(text: str) -> tuple[float, float]:
    match = re.search(r"([\d,.]+)\s*[-—–至]\s*([\d,.]+)", text)
    if not match:
        raise ValueError(f"无法解析价格区间：{text}")
    return tuple(float(value.replace(",", "")) for value in match.groups())


def fetch_vd3_asset(max_pages: int = 60) -> dict:
    """遍历公开归档，拉取全部可获得的饲料级维生素 D3 报价。"""
    points_by_date = _existing_series_by_code("VD3")
    points_by_date.update(_reference_points_by_date("VD3"))
    candidates: dict[str, str] = {}
    seen_article_urls = set()
    consecutive_empty_pages = 0

    for page in range(1, max_pages + 1):
        page_url = (
            FEEDTRADE_LIST_URL
            if page == 1
            else FEEDTRADE_LIST_URL.replace("index.html", f"index_{page}.html")
        )
        list_soup = BeautifulSoup(_get_html(page_url), "html.parser")
        page_candidates = 0
        for link in list_soup.select("a[href]"):
            href = urljoin(page_url, link.get("href", ""))
            match = re.search(r"/vitamin/(\d{4}-\d{2}-\d{2})/\d+\.html", href)
            if not match or href in seen_article_urls:
                continue
            seen_article_urls.add(href)
            point_date = match.group(1)
            if point_date not in points_by_date:
                candidates[point_date] = href
            page_candidates += 1
        if page_candidates == 0:
            consecutive_empty_pages += 1
            if consecutive_empty_pages >= 2:
                break
        else:
            consecutive_empty_pages = 0

    def parse_article(item: tuple[str, str]) -> tuple[str, dict] | None:
        article_date, article_url = item
        try:
            article_soup = BeautifulSoup(_get_html(article_url), "html.parser")
        except requests.RequestException:
            return None
        for row in article_soup.select("tr"):
            cells = row.find_all(["td", "th"])
            if not cells or cells[0].get_text(" ", strip=True).upper() != "D3":
                continue
            if len(cells) < 3:
                return None
            try:
                price_low, price_high = _parse_price_range(
                    cells[2].get_text(" ", strip=True)
                )
            except ValueError:
                return None
            return (
                article_date,
                {
                    "date": article_date,
                    "price": (price_low + price_high) / 2,
                    "price_low": price_low,
                    "price_high": price_high,
                    "source_url": article_url,
                },
            )
        return None

    with ThreadPoolExecutor(max_workers=6) as executor:
        for parsed in executor.map(parse_article, candidates.items()):
            if parsed:
                points_by_date[parsed[0]] = parsed[1]
    if not points_by_date:
        raise ValueError("饲料行业信息网未找到维生素 D3 报价")

    series = [points_by_date[key] for key in sorted(points_by_date)]
    return {
        "code": "VD3",
        "name": "维生素D3（饲料级）",
        "unit": "元/公斤",
        "source": "饲料行业信息网",
        "category": "饲料添加剂",
        "latest": series[-1],
        "series": series,
    }


def _number(text: str) -> float:
    return float(text.replace(",", ""))


def fetch_vlcc_assets(max_pages: int = 60) -> list[dict]:
    """遍历信德海事公开周报，汇总全部可获得的 VLCC 运价历史。"""
    configs = {
        "TD3C": {
            "name": "TD3C航线日租金（中东湾→中国VLCC）",
            "ws_name": "TD3C运价WS（中东湾→中国VLCC）",
        },
        "TD15": {
            "name": "TD15航线日租金（西非→中国VLCC）",
            "ws_name": "TD15运价WS（西非→中国VLCC）",
        },
    }
    asset_codes = ("TD3C", "TD3C_WS", "TD15", "TD15_WS")
    points_by_code = {
        code: _existing_series_by_code(code)
        for code in asset_codes
    }
    reports_by_id = {}
    page_size = 100
    for page in range(1, max_pages + 1):
        response = requests.post(
            f"{XINDE_API_ROOT}/articles/search",
            json={
                "keyword": "波交所每周运费市场报告",
                "pageNo": page,
                "pageSize": page_size,
                "columnId": 0,
                "topColumnId": 0,
                "createId": "",
                "column": "",
                "order": "",
                "type": 3,
            },
            headers=REQUEST_HEADERS,
            timeout=20,
        )
        response.raise_for_status()
        result = response.json().get("result", {})
        records = result.get("records", [])
        if not records:
            break
        for record in records:
            if (
                "波交所每周运费市场报告" in record.get("title", "")
                and "TD3C" in record.get("content", "")
                and "TD15" in record.get("content", "")
            ):
                reports_by_id[record["id"]] = record
        if page >= int(result.get("pages") or page) or len(records) < page_size:
            break

    if not reports_by_id and not all(points_by_code.values()):
        raise ValueError("信德海事网未找到 VLCC 周报")

    for report in reports_by_id.values():
        title = report.get("title", "")
        date_match = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", title)
        if not date_match:
            continue
        report_date = "-".join(
            [
                date_match.group(1),
                date_match.group(2).zfill(2),
                date_match.group(3).zfill(2),
            ]
        )
        if all(report_date in points_by_code[code] for code in asset_codes):
            continue
        source_url = f"https://www.xindemarinenews.com.cn/article?id={report['id']}"
        paragraphs = [
            node.get_text(" ", strip=True)
            for node in BeautifulSoup(
                report.get("content", ""),
                "html.parser",
            ).find_all("p")
        ]
        for code in configs:
            paragraph = next((text for text in paragraphs if code in text), "")
            ws_values = re.findall(
                r"WS\s*([\d,.]+)",
                paragraph,
            )
            tce_match = re.search(
                r"(?:TCE|等价期租)[^。；]*?([\d,.]+)\s*美元",
                paragraph,
            )
            if not ws_values or not tce_match:
                continue
            ws_price = _number(ws_values[-1])
            tce_price = _number(tce_match.group(1))
            points_by_code[code][report_date] = {
                "date": report_date,
                "price": tce_price,
                "price_low": None,
                "price_high": None,
                "source_url": source_url,
            }
            points_by_code[f"{code}_WS"][report_date] = {
                "date": report_date,
                "price": ws_price,
                "price_low": None,
                "price_high": None,
                "source_url": source_url,
            }

    assets = []
    for code, config in configs.items():
        for asset_code, name, unit in (
            (code, config["name"], "美元/天"),
            (f"{code}_WS", config["ws_name"], "WS点数"),
        ):
            series = [
                points_by_code[asset_code][key]
                for key in sorted(points_by_code[asset_code])
            ]
            if not series:
                raise ValueError(f"无法从 VLCC 周报解析 {asset_code} 运价")
            assets.append(
                {
                    "code": asset_code,
                    "name": name,
                    "unit": unit,
                    "source": "波罗的海交易所（信德海事网转载）",
                    "category": "VLCC油运",
                    "latest": series[-1],
                    "series": series,
                }
            )
    return assets


def fetch_monkey_asset(
    history_days: int = MAX_HISTORY_DAYS,
    max_pages: int = 20,
) -> dict:
    """遍历政府采购公告，收集可识别的食蟹猴成交单价。"""
    today = date.today()
    points_by_date = _existing_series_by_code("MONKEY")
    existing_urls = {
        point.get("source_url")
        for point in points_by_date.values()
        if point.get("source_url")
    }
    links = []
    seen_links = set()
    for page in range(1, max_pages + 1):
        response = requests.get(
            CCGP_SEARCH_URL,
            params={
                "searchtype": 1,
                "page_index": page,
                "bidSort": 7,
                "bidType": 7,
                "dbselect": "bidx",
                "kw": "食蟹猴",
                "start_time": (
                    today - timedelta(days=history_days)
                ).strftime("%Y:%m:%d"),
                "end_time": today.strftime("%Y:%m:%d"),
                "timeType": 6,
            },
            headers={**REQUEST_HEADERS, "Referer": "https://www.ccgp.gov.cn/"},
            timeout=20,
        )
        response.raise_for_status()
        if response.encoding == "ISO-8859-1":
            response.encoding = response.apparent_encoding
        if "访问过于频繁" in response.text:
            raise RuntimeError("中国政府采购网限制了搜索访问")
        search_soup = BeautifulSoup(response.text, "html.parser")
        page_links = [
            urljoin(CCGP_SEARCH_URL, link.get("href", ""))
            for link in search_soup.select("a[href]")
            if "食蟹猴" in link.get_text(" ", strip=True)
        ]
        new_links = [
            link
            for link in page_links
            if link not in seen_links and link not in existing_urls
        ]
        if not page_links:
            break
        links.extend(new_links)
        seen_links.update(page_links)
        if not new_links:
            break

    for source_url in links:
        article_soup = BeautifulSoup(_get_html(source_url), "html.parser")
        date_node = article_soup.select_one('meta[name="PubDate"]')
        unit_price = None
        for table in article_soup.select("table"):
            rows = table.select("tr")
            price_index = None
            for row_index, row in enumerate(rows):
                cells = row.find_all(["td", "th"])
                labels = [cell.get_text(" ", strip=True) for cell in cells]
                price_index = next(
                    (
                        index
                        for index, label in enumerate(labels)
                        if "货物单价" in label
                    ),
                    None,
                )
                if price_index is None:
                    continue
                for data_row in rows[row_index + 1 :]:
                    values = [
                        cell.get_text(" ", strip=True)
                        for cell in data_row.find_all(["td", "th"])
                    ]
                    if (
                        len(values) > price_index
                        and any("食蟹猴" in value for value in values)
                    ):
                        number_match = re.search(r"[\d,.]+", values[price_index])
                        if number_match:
                            unit_price = _number(number_match.group())
                            break
                break
            if unit_price is not None:
                break
        if unit_price is None or not date_node:
            continue
        point_date = date_node.get("content", "")[:10]
        points_by_date[point_date] = {
            "date": point_date,
            "price": unit_price / 10000,
            "price_low": None,
            "price_high": None,
            "source_url": source_url,
        }
    if not points_by_date:
        raise ValueError("采购公告中未找到食蟹猴单价")
    series = [points_by_date[key] for key in sorted(points_by_date)]
    return {
        "code": "MONKEY",
        "name": "实验猴（食蟹猴）",
        "unit": "万元/只",
        "source": "中国政府采购网",
        "category": "生物医药上游",
        "latest": series[-1],
        "series": series,
    }


def load_existing_payload(output_path: Path = OUTPUT_PATH) -> dict:
    if not output_path.exists():
        return {"assets": []}
    return json.loads(output_path.read_text(encoding="utf-8"))


def merge_assets(existing_assets: list[dict], updates: list[dict]) -> list[dict]:
    assets_by_code = {asset["code"]: asset for asset in existing_assets}
    for update in updates:
        existing = assets_by_code.get(update["code"], {})
        points_by_date = {
            point["date"]: point
            for point in existing.get("series", [])
            if point.get("date")
        }
        points_by_date.update(
            {
                point["date"]: point
                for point in update.get("series", [])
                if point.get("date")
            }
        )
        series = [points_by_date[key] for key in sorted(points_by_date)]
        merged = {**existing, **update, "series": series}
        merged["latest"] = series[-1] if series else None
        assets_by_code[update["code"]] = merged

    def asset_sort_key(asset: dict) -> tuple[int, int, str]:
        category = asset.get("category", "其他")
        category_index = (
            CATEGORY_ORDER.index(category)
            if category in CATEGORY_ORDER
            else len(CATEGORY_ORDER)
        )
        return (
            category_index,
            ASSET_ORDER.get(asset["code"], len(ASSET_ORDER)),
            asset["code"],
        )

    return sorted(assets_by_code.values(), key=asset_sort_key)


def export_json(assets: list[dict], output_path: Path = OUTPUT_PATH) -> int:
    categories = [
        {
            "name": category,
            "asset_codes": [
                asset["code"] for asset in assets if asset.get("category") == category
            ],
        }
        for category in CATEGORY_ORDER
        if any(asset.get("category") == category for asset in assets)
    ]
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    payload = {
        "data_type": "关注资产价格",
        "generated_at": now,
        "source_updated_at": now,
        "categories": categories,
        "assets": assets,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(".json.tmp")
    temporary_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary_path.replace(output_path)

    point_count = sum(len(asset.get("series", [])) for asset in assets)
    print(
        f"已导出 {len(assets)} 个资产、{point_count} 条价格记录至 {output_path}",
        flush=True,
    )
    return len(assets)


def update_small_metals_only(
    output_path: Path = OUTPUT_PATH,
    history_days: int = MAX_HISTORY_DAYS,
) -> int:
    """单独刷新现有 JSON 中的小金属价格。"""
    if not output_path.exists():
        raise FileNotFoundError(f"资产价格 JSON 不存在：{output_path}")

    payload = load_existing_payload(output_path)
    small_metal_assets = fetch_small_metal_assets(history_days)
    assets = merge_assets(payload.get("assets", []), small_metal_assets)
    export_json(assets, output_path)
    print(
        "已单独刷新小金属价格："
        + "、".join(
            f"{asset['name']} {len(asset['series'])} 条"
            for asset in small_metal_assets
        ),
        flush=True,
    )
    return len(small_metal_assets)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="导出前拉取全部关注资产的最新价格",
    )
    parser.add_argument(
        "--fetch-antimony-only",
        action="store_true",
        help="兼容旧命令：仅刷新现有 JSON 中的小金属价格",
    )
    parser.add_argument(
        "--fetch-small-metals-only",
        action="store_true",
        help="仅刷新现有 JSON 中的国内、国外小金属价格",
    )
    parser.add_argument(
        "--history-days",
        type=int,
        default=MAX_HISTORY_DAYS,
        help=f"历史回溯天数，最多 {MAX_HISTORY_DAYS} 天（约10年）",
    )
    args = parser.parse_args()
    if not 1 <= args.history_days <= MAX_HISTORY_DAYS:
        parser.error(f"--history-days 必须在 1 到 {MAX_HISTORY_DAYS} 之间")

    if args.fetch_antimony_only or args.fetch_small_metals_only:
        update_small_metals_only(history_days=args.history_days)
        return 0

    payload = load_existing_payload()
    assets = payload.get("assets", [])
    fetch_returncode = 0
    if args.fetch:
        fetchers = [
            (
                "硫磺",
                {"SULFUR"},
                lambda: fetch_sulfur_asset(args.history_days),
            ),
            ("硫铁矿", {"PYRITE"}, fetch_pyrite_asset),
            (
                "氧化铝",
                {"ALUMINA"},
                lambda: fetch_alumina_asset(args.history_days),
            ),
            (
                "电解铝",
                {"ALUMINUM"},
                lambda: fetch_aluminum_asset(args.history_days),
            ),
            ("磷矿石", {"PHOSPHATE_ROCK"}, fetch_phosphate_rock_asset),
            ("分散染料还原物", {"DYE_REDUCTION"}, fetch_dye_reduction_asset),
            (
                "血液制品",
                {"BLOOD_ALBUMIN", "BLOOD_IVIG"},
                fetch_blood_product_assets,
            ),
            (
                "国内、国外小金属",
                set(SMM_ASSETS),
                lambda: fetch_small_metal_assets(args.history_days),
            ),
            ("维生素 D3", {"VD3"}, fetch_vd3_asset),
            (
                "VLCC 油运",
                {"TD3C", "TD3C_WS", "TD15", "TD15_WS"},
                fetch_vlcc_assets,
            ),
            (
                "实验猴",
                {"MONKEY"},
                lambda: fetch_monkey_asset(args.history_days),
            ),
        ]
        existing_codes = {asset.get("code") for asset in assets}
        for label, expected_codes, fetcher in fetchers:
            try:
                result = fetcher()
                updates = result if isinstance(result, list) else [result]
                assets = merge_assets(assets, updates)
                print(f"已拉取{label}价格。", flush=True)
            except (
                requests.RequestException,
                json.JSONDecodeError,
                RuntimeError,
                KeyError,
                TypeError,
                ValueError,
            ) as error:
                print(
                    f"[WARN] {label}价格拉取失败，将保留上次数据：{error}",
                    flush=True,
                )
                if not expected_codes.issubset(existing_codes):
                    fetch_returncode = 1

    asset_count = export_json(assets)

    if asset_count == 0:
        print("[ERROR] 没有可导出的资产数据。", flush=True)
        return 1
    return fetch_returncode


if __name__ == "__main__":
    raise SystemExit(main())
