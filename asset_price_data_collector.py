#!/usr/bin/env python3
"""拉取 AssetPriceMonitor 数据并导出为 HousePrice 可读取的 JSON。"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import requests


HOUSE_PRICE_ROOT = Path(__file__).resolve().parent
DEFAULT_ASSET_ROOT = HOUSE_PRICE_ROOT.parent / "AssetPriceMonitor"
OUTPUT_PATH = HOUSE_PRICE_ROOT / "results" / "asset_price_data.json"
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


def get_asset_root() -> Path:
    configured = os.environ.get("ASSET_PRICE_MONITOR_PATH")
    return Path(configured).expanduser().resolve() if configured else DEFAULT_ASSET_ROOT


def fetch_latest(asset_root: Path) -> int:
    main_script = asset_root / "main.py"
    if not main_script.exists():
        raise FileNotFoundError(f"未找到 AssetPriceMonitor：{main_script}")

    print(f"开始拉取关注资产价格：{asset_root}", flush=True)
    result = subprocess.run(
        [sys.executable, str(main_script), "fetch"],
        cwd=asset_root,
        check=False,
    )
    if result.returncode:
        print(
            f"[WARN] 部分资产拉取失败（退出码 {result.returncode}），将导出已成功写入的数据。",
            flush=True,
        )
    return result.returncode


def export_json(
    asset_root: Path,
    output_path: Path = OUTPUT_PATH,
    supplemental_assets: list[dict] | None = None,
) -> int:
    db_path = asset_root / "data" / "prices.db"
    if not db_path.exists():
        raise FileNotFoundError(f"资产价格数据库不存在：{db_path}")

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT
                a.code, a.name, a.unit, a.source,
                p.ts, p.price, p.price_low, p.price_high,
                p.source_url, p.fetched_at
            FROM assets a
            LEFT JOIN prices p ON p.asset_code = a.code
            ORDER BY a.code, p.ts
            """
        ).fetchall()

    assets_by_code: dict[str, dict] = {}
    latest_fetched_at = None

    for row in rows:
        code = row["code"]
        asset = assets_by_code.setdefault(
            code,
            {
                "code": code,
                "name": row["name"],
                "unit": row["unit"],
                "source": row["source"],
                "category": CATEGORY_BY_CODE.get(code, "其他"),
                "latest": None,
                "series": [],
            },
        )
        if row["ts"] is None:
            continue

        point = {
            "date": row["ts"],
            "price": row["price"],
            "price_low": row["price_low"],
            "price_high": row["price_high"],
            "source_url": row["source_url"] or "",
        }
        asset["series"].append(point)
        asset["latest"] = point

        fetched_at = row["fetched_at"]
        if fetched_at and (latest_fetched_at is None or fetched_at > latest_fetched_at):
            latest_fetched_at = fetched_at

    def asset_sort_key(asset: dict) -> tuple[int, str]:
        category = asset["category"]
        category_index = (
            CATEGORY_ORDER.index(category)
            if category in CATEGORY_ORDER
            else len(CATEGORY_ORDER)
        )
        return category_index, asset["code"]

    for asset in supplemental_assets or []:
        assets_by_code[asset["code"]] = asset

    assets = sorted(assets_by_code.values(), key=asset_sort_key)
    categories = [
        {
            "name": category,
            "asset_codes": [
                asset["code"] for asset in assets if asset["category"] == category
            ],
        }
        for category in CATEGORY_ORDER
        if any(asset["category"] == category for asset in assets)
    ]

    payload = {
        "data_type": "关注资产价格",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source_updated_at": latest_fetched_at,
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

    point_count = sum(len(asset["series"]) for asset in assets)
    print(
        f"已导出 {len(assets)} 个资产、{point_count} 条价格记录至 {output_path}",
        flush=True,
    )
    return len(assets)


def update_small_metals_only(output_path: Path = OUTPUT_PATH) -> int:
    """不依赖 AssetPriceMonitor，单独刷新现有 JSON 中的小金属价格。"""
    if not output_path.exists():
        raise FileNotFoundError(f"资产价格 JSON 不存在：{output_path}")

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    small_metal_assets = fetch_small_metal_assets()
    assets_by_code = {
        asset["code"]: asset
        for asset in payload.get("assets", [])
    }
    for asset in small_metal_assets:
        assets_by_code[asset["code"]] = asset

    def asset_sort_key(asset: dict) -> tuple[int, str]:
        category = asset.get("category", "其他")
        category_index = (
            CATEGORY_ORDER.index(category)
            if category in CATEGORY_ORDER
            else len(CATEGORY_ORDER)
        )
        return category_index, asset["code"]

    assets = sorted(assets_by_code.values(), key=asset_sort_key)
    payload["assets"] = assets
    payload["categories"] = [
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
    payload["generated_at"] = now
    payload["source_updated_at"] = now

    temporary_path = output_path.with_suffix(".json.tmp")
    temporary_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary_path.replace(output_path)
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
        help="导出前先调用 AssetPriceMonitor 拉取最新价格",
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

    asset_root = get_asset_root()
    fetch_returncode = fetch_latest(asset_root) if args.fetch else 0
    small_metal_assets = load_existing_small_metal_assets()
    if args.fetch:
        try:
            small_metal_assets = fetch_small_metal_assets()
            print("已拉取国内、国外小金属价格。", flush=True)
        except (requests.RequestException, RuntimeError, KeyError, ValueError) as error:
            print(
                f"[WARN] 小金属价格拉取失败，将保留上次数据：{error}",
                flush=True,
            )
            if not small_metal_assets:
                fetch_returncode = fetch_returncode or 1

    asset_count = export_json(
        asset_root,
        supplemental_assets=small_metal_assets,
    )

    if asset_count == 0:
        print("[ERROR] 没有可导出的资产数据。", flush=True)
        return 1
    return fetch_returncode


if __name__ == "__main__":
    raise SystemExit(main())
