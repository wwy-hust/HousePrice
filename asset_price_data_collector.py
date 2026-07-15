#!/usr/bin/env python3
"""拉取 AssetPriceMonitor 数据并导出为 HousePrice 可读取的 JSON。"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path


HOUSE_PRICE_ROOT = Path(__file__).resolve().parent
DEFAULT_ASSET_ROOT = HOUSE_PRICE_ROOT.parent / "AssetPriceMonitor"
OUTPUT_PATH = HOUSE_PRICE_ROOT / "results" / "asset_price_data.json"

CATEGORY_BY_CODE = {
    "SULFUR": "大宗商品",
    "VD3": "饲料添加剂",
    "TD3C": "VLCC油运",
    "TD3C_WS": "VLCC油运",
    "TD15": "VLCC油运",
    "TD15_WS": "VLCC油运",
    "MONKEY": "生物医药上游",
}
CATEGORY_ORDER = ["大宗商品", "饲料添加剂", "VLCC油运", "生物医药上游"]


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


def export_json(asset_root: Path, output_path: Path = OUTPUT_PATH) -> int:
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="导出前先调用 AssetPriceMonitor 拉取最新价格",
    )
    args = parser.parse_args()

    asset_root = get_asset_root()
    fetch_returncode = fetch_latest(asset_root) if args.fetch else 0
    asset_count = export_json(asset_root)

    if asset_count == 0:
        print("[ERROR] 没有可导出的资产数据。", flush=True)
        return 1
    return fetch_returncode


if __name__ == "__main__":
    raise SystemExit(main())
