#!/usr/bin/env python3
"""直接拉取关注资产价格并导出为 HousePrice 可读取的 JSON。"""

from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


HOUSE_PRICE_ROOT = Path(__file__).resolve().parent
OUTPUT_PATH = HOUSE_PRICE_ROOT / "results" / "asset_price_data.json"
REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0 (HousePrice asset collector)"}
SULFUR_CHART_URL = (
    "https://www.100ppi.com/graph/cindex.php?f=graph_ppid_ave&ppid=427"
)
SULFUR_DETAIL_URL = "https://www.100ppi.com/rawmex/detail-427.html"
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

CATEGORY_BY_CODE = {
    "SULFUR": "大宗商品",
    "SB_CN": "小金属",
    "SB_INTL": "小金属",
    "W_CN": "小金属",
    "W_INTL": "小金属",
    "VD3": "饲料添加剂",
    "TD3C": "VLCC油运",
    "TD3C_WS": "VLCC油运",
    "TD15": "VLCC油运",
    "TD15_WS": "VLCC油运",
    "MONKEY": "生物医药上游",
}
CATEGORY_ORDER = [
    "大宗商品",
    "小金属",
    "饲料添加剂",
    "VLCC油运",
    "生物医药上游",
]


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


def fetch_small_metal_assets(history_days: int = 730) -> list[dict]:
    """拉取国内和国外小金属价格，并转换为前端通用资产结构。"""
    product_ids = ",".join(
        config["product_id"] for config in SMM_ASSETS.values()
    )
    today = date.today()
    params = {
        "product_ids": product_ids,
        "begin_date": (today - timedelta(days=history_days)).isoformat(),
        "end_date": today.isoformat(),
    }
    history_by_id = {
        item["product_id"]: item
        for item in _get_smm_data("history_price", params)
    }
    latest_by_id = {
        item["product_id"]: item
        for item in _get_smm_data("latest_price", {"product_ids": product_ids})
    }

    assets = []
    for code, config in SMM_ASSETS.items():
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
                "category": "小金属",
                "latest": series[-1],
                "series": series,
            }
        )
    return assets


def fetch_antimony_assets(history_days: int = 730) -> list[dict]:
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


def fetch_sulfur_asset() -> dict:
    unpacked = _unpack_packer(_get_html(SULFUR_CHART_URL))
    dates_match = re.search(
        r"xAxis:\{.*?data:\[(?P<data>.*?)\]\},yAxis:",
        unpacked,
        re.DOTALL,
    )
    prices_match = re.search(
        r"series:\[.*?data:\[(?P<data>[\d.,\s]+)\]",
        unpacked,
        re.DOTALL,
    )
    if not dates_match or not prices_match:
        raise ValueError("无法解析生意社硫磺价格序列")

    dates = re.findall(r"\d{4}-\d{2}-\d{2}", dates_match.group("data"))
    prices = [
        float(value.replace(",", ""))
        for value in prices_match.group("data").split(",")
        if value.strip()
    ]
    if not dates or len(dates) != len(prices):
        raise ValueError("生意社硫磺价格日期与数值数量不一致")

    series = [
        {
            "date": point_date,
            "price": price,
            "price_low": None,
            "price_high": None,
            "source_url": SULFUR_CHART_URL,
        }
        for point_date, price in zip(dates, prices)
    ]
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


def _parse_price_range(text: str) -> tuple[float, float]:
    match = re.search(r"([\d,.]+)\s*[-—–至]\s*([\d,.]+)", text)
    if not match:
        raise ValueError(f"无法解析价格区间：{text}")
    return tuple(float(value.replace(",", "")) for value in match.groups())


def fetch_vd3_asset() -> dict:
    list_soup = BeautifulSoup(_get_html(FEEDTRADE_LIST_URL), "html.parser")
    candidates = []
    for link in list_soup.select("a[href]"):
        href = urljoin(FEEDTRADE_LIST_URL, link.get("href", ""))
        match = re.search(r"/vitamin/(\d{4}-\d{2}-\d{2})/\d+\.html", href)
        if match:
            candidates.append((match.group(1), href))
    if not candidates:
        raise ValueError("饲料行业信息网未找到维生素行情文章")

    article_date, article_url = max(candidates)
    article_soup = BeautifulSoup(_get_html(article_url), "html.parser")
    for row in article_soup.select("tr"):
        cells = row.find_all(["td", "th"])
        if not cells or cells[0].get_text(" ", strip=True).upper() != "D3":
            continue
        if len(cells) < 3:
            break
        price_low, price_high = _parse_price_range(
            cells[2].get_text(" ", strip=True)
        )
        point = {
            "date": article_date,
            "price": (price_low + price_high) / 2,
            "price_low": price_low,
            "price_high": price_high,
            "source_url": article_url,
        }
        return {
            "code": "VD3",
            "name": "维生素D3（饲料级）",
            "unit": "元/公斤",
            "source": "饲料行业信息网",
            "category": "饲料添加剂",
            "latest": point,
            "series": [point],
        }
    raise ValueError("最新行情文章中未找到维生素 D3 报价")


def _number(text: str) -> float:
    return float(text.replace(",", ""))


def fetch_vlcc_assets() -> list[dict]:
    response = requests.post(
        f"{XINDE_API_ROOT}/articles/search",
        json={
            "keyword": "波交所每周运费市场报告",
            "pageNo": 1,
            "pageSize": 100,
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
    records = response.json().get("result", {}).get("records", [])
    reports = [
        record
        for record in records
        if "波交所每周运费市场报告" in record.get("title", "")
        and "TD3C" in record.get("content", "")
        and "TD15" in record.get("content", "")
    ]
    if not reports:
        raise ValueError("信德海事网未找到最新 VLCC 周报")

    report = max(reports, key=lambda item: item.get("createTime", ""))
    title = report["title"]
    date_match = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", title)
    if not date_match:
        raise ValueError(f"无法识别 VLCC 周报日期：{title}")
    report_date = "-".join(
        [date_match.group(1), date_match.group(2).zfill(2), date_match.group(3).zfill(2)]
    )
    source_url = f"https://www.xindemarinenews.com.cn/article?id={report['id']}"
    paragraphs = [
        node.get_text(" ", strip=True)
        for node in BeautifulSoup(report["content"], "html.parser").find_all("p")
    ]

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
    assets = []
    for code, config in configs.items():
        paragraph = next((text for text in paragraphs if code in text), "")
        match = re.search(
            rf"{code}.*?WS\s*([\d,.]+).*?TCE[^。；]*?([\d,.]+)\s*美元",
            paragraph,
        )
        if not match:
            raise ValueError(f"无法从 VLCC 周报解析 {code} 运价")
        ws_price, tce_price = map(_number, match.groups())
        for asset_code, name, unit, price in (
            (code, config["name"], "美元/天", tce_price),
            (f"{code}_WS", config["ws_name"], "WS点数", ws_price),
        ):
            point = {
                "date": report_date,
                "price": price,
                "price_low": None,
                "price_high": None,
                "source_url": source_url,
            }
            assets.append(
                {
                    "code": asset_code,
                    "name": name,
                    "unit": unit,
                    "source": "波罗的海交易所（信德海事网转载）",
                    "category": "VLCC油运",
                    "latest": point,
                    "series": [point],
                }
            )
    return assets


def fetch_monkey_asset() -> dict:
    today = date.today()
    response = requests.get(
        CCGP_SEARCH_URL,
        params={
            "searchtype": 1,
            "page_index": 1,
            "bidSort": 7,
            "bidType": 7,
            "dbselect": "bidx",
            "kw": "食蟹猴",
            "start_time": (today - timedelta(days=370)).strftime("%Y:%m:%d"),
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
    links = [
        urljoin(CCGP_SEARCH_URL, link.get("href", ""))
        for link in search_soup.select("a[href]")
        if "食蟹猴" in link.get_text(" ", strip=True)
    ]
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
        point = {
            "date": date_node.get("content", "")[:10],
            "price": unit_price / 10000,
            "price_low": None,
            "price_high": None,
            "source_url": source_url,
        }
        return {
            "code": "MONKEY",
            "name": "实验猴（食蟹猴）",
            "unit": "万元/只",
            "source": "中国政府采购网",
            "category": "生物医药上游",
            "latest": point,
            "series": [point],
        }
    raise ValueError("采购公告中未找到食蟹猴单价")


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

    def asset_sort_key(asset: dict) -> tuple[int, str]:
        category = asset.get("category", "其他")
        category_index = (
            CATEGORY_ORDER.index(category)
            if category in CATEGORY_ORDER
            else len(CATEGORY_ORDER)
        )
        return category_index, asset["code"]

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


def update_small_metals_only(output_path: Path = OUTPUT_PATH) -> int:
    """单独刷新现有 JSON 中的小金属价格。"""
    if not output_path.exists():
        raise FileNotFoundError(f"资产价格 JSON 不存在：{output_path}")

    payload = load_existing_payload(output_path)
    small_metal_assets = fetch_small_metal_assets()
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
    args = parser.parse_args()

    if args.fetch_antimony_only or args.fetch_small_metals_only:
        update_small_metals_only()
        return 0

    payload = load_existing_payload()
    assets = payload.get("assets", [])
    fetch_returncode = 0
    if args.fetch:
        fetchers = [
            ("硫磺", {"SULFUR"}, fetch_sulfur_asset),
            ("国内、国外小金属", set(SMM_ASSETS), fetch_small_metal_assets),
            ("维生素 D3", {"VD3"}, fetch_vd3_asset),
            (
                "VLCC 油运",
                {"TD3C", "TD3C_WS", "TD15", "TD15_WS"},
                fetch_vlcc_assets,
            ),
            ("实验猴", {"MONKEY"}, fetch_monkey_asset),
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
