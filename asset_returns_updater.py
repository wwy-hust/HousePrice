#!/usr/bin/env python3
"""更新大类资产排名页当前年份的 YTD 收益率。"""

from __future__ import annotations

import argparse
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import akshare as ak
import pandas as pd
import requests


ROOT = Path(__file__).resolve().parent
OUTPUT_PATH = ROOT / "results" / "asset_returns_ranking.json"
HOUSE_DATA_PATH = ROOT / "results" / "used_house_basic_index.json"


def calculate_frame_return(
    frame: pd.DataFrame,
    year: int,
    *,
    date_column: str = "date",
    value_column: str = "close",
) -> tuple[float, str]:
    data = frame.copy()
    data[date_column] = pd.to_datetime(data[date_column], errors="coerce")
    data[value_column] = pd.to_numeric(data[value_column], errors="coerce")
    data = data.dropna(subset=[date_column, value_column]).sort_values(date_column)
    data = data[data[date_column].dt.year == year]
    if len(data) < 2:
        raise ValueError(f"{year} 年有效数据不足")

    first_value = float(data.iloc[0][value_column])
    last_value = float(data.iloc[-1][value_column])
    if first_value == 0 or not math.isfinite(first_value + last_value):
        raise ValueError("行情数据包含无效价格")

    latest_date = data.iloc[-1][date_column].date().isoformat()
    return round((last_value / first_value - 1) * 100, 2), latest_date


def fetch_house_return(year: int) -> tuple[float, str]:
    payload = json.loads(HOUSE_DATA_PATH.read_text(encoding="utf-8"))
    beijing = next(
        city for city in payload.get("cities", []) if city.get("city") == "北京"
    )
    points = sorted(
        (
            point
            for point in beijing.get("raw_data", [])
            if str(point.get("date", "")).startswith(f"{year}-")
            and point.get("month_on_month") is not None
        ),
        key=lambda point: point["date"],
    )
    if not points:
        raise ValueError(f"北京二手房暂无 {year} 年数据")

    cumulative = 1.0
    for point in points:
        cumulative *= float(point["month_on_month"]) / 100
    return round((cumulative - 1) * 100, 2), points[-1]["date"]


def fetch_crypto_return(coin_id: str, year: int) -> tuple[float, str]:
    response = requests.get(
        f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart",
        params={"vs_currency": "usd", "days": "365", "interval": "daily"},
        headers={"User-Agent": "HousePrice asset-returns updater/1.0"},
        timeout=30,
    )
    response.raise_for_status()
    points = []
    for timestamp, price in response.json().get("prices", []):
        date = datetime.fromtimestamp(timestamp / 1000, timezone.utc)
        if date.year == year:
            points.append((date, float(price)))
    if len(points) < 2:
        raise ValueError(f"{coin_id} 暂无 {year} 年完整行情")
    points.sort(key=lambda point: point[0])
    value = round((points[-1][1] / points[0][1] - 1) * 100, 2)
    return value, points[-1][0].date().isoformat()


def carry_forward_deposit_rate(payload: dict) -> tuple[float, str]:
    for year in sorted(payload.get("returns", {}), key=int, reverse=True):
        value = payload["returns"][year].get("deposit")
        if value is not None:
            return float(value), f"{year}-12-31"
    raise ValueError("未找到一年期定期存款利率")


def build_fetchers(payload: dict) -> dict[str, Callable[[int], tuple[float, str]]]:
    return {
        "house": fetch_house_return,
        "deposit": lambda _year: carry_forward_deposit_rate(payload),
        "corporate_bond": lambda year: calculate_frame_return(
            ak.bond_index_general_cbond("企业债总指数", "财富", "总值"),
            year,
            value_column="value",
        ),
        "gold": lambda year: calculate_frame_return(
            ak.futures_foreign_hist("GC"), year
        ),
        "oil": lambda year: calculate_frame_return(
            ak.futures_foreign_hist("CL"), year
        ),
        "sse50": lambda year: calculate_frame_return(
            ak.stock_zh_index_daily("sh000016"), year
        ),
        "csi300": lambda year: calculate_frame_return(
            ak.stock_zh_index_daily("sh000300"), year
        ),
        "chinext": lambda year: calculate_frame_return(
            ak.stock_zh_index_daily("sz399006"), year
        ),
        "star50": lambda year: calculate_frame_return(
            ak.stock_zh_index_daily("sh000688"), year
        ),
        "nasdaq": lambda year: calculate_frame_return(
            ak.stock_us_daily(".IXIC", ""), year
        ),
        "sp500": lambda year: calculate_frame_return(
            ak.stock_us_daily(".INX", ""), year
        ),
        "dow": lambda year: calculate_frame_return(
            ak.stock_us_daily(".DJI", ""), year
        ),
        "sox": lambda year: calculate_frame_return(
            ak.stock_us_daily(".SOX", ""), year
        ),
        "nikkei": lambda year: calculate_frame_return(
            ak.index_global_hist_sina("日经225指数"), year
        ),
        "kospi": lambda year: calculate_frame_return(
            ak.index_global_hist_sina("首尔综合指数"), year
        ),
        "bitcoin": lambda year: fetch_crypto_return("bitcoin", year),
        "ethereum": lambda year: fetch_crypto_return("ethereum", year),
    }


def update_current_year(output_path: Path, dry_run: bool = False) -> int:
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    current_year = datetime.now().astimezone().year
    asset_names = {
        asset["key"]: asset.get("short_name", asset["name"])
        for asset in payload.get("assets", [])
    }
    current_returns = dict(payload.get("returns", {}).get(str(current_year), {}))
    latest_dates = {}
    success_count = 0

    print(f"开始更新 {current_year} 年 YTD 收益率", flush=True)
    for key, fetcher in build_fetchers(payload).items():
        name = asset_names.get(key, key)
        for attempt in range(2):
            try:
                value, latest_date = fetcher(current_year)
                current_returns[key] = value
                latest_dates[key] = latest_date
                success_count += 1
                print(
                    f"[OK] {name}: {value:+.2f}%（截至 {latest_date}）",
                    flush=True,
                )
                break
            except Exception as error:
                if attempt == 0:
                    time.sleep(0.6)
                    continue
                print(f"[WARN] {name}: {error}", flush=True)

    if not success_count:
        print("[ERROR] 未能更新任何资产", flush=True)
        return 1

    if "stoxx600" not in current_returns:
        print("[WARN] 欧洲STOXX600：当前数据源暂不支持自动更新", flush=True)

    payload.setdefault("returns", {})[str(current_year)] = current_returns
    payload["end_year"] = max(int(payload.get("end_year", current_year)), current_year)
    payload["partial_year"] = current_year
    payload["generated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    payload["latest_dates"] = latest_dates

    if dry_run:
        print(
            f"试运行完成：成功获取 {success_count} 项，不写入文件",
            flush=True,
        )
        return 0

    temporary_path = output_path.with_suffix(".json.tmp")
    temporary_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary_path.replace(output_path)
    print(
        f"更新完成：{success_count} 项数据已写入 {output_path}",
        flush=True,
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="拉取并校验，但不写入文件")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH, help="输出 JSON 路径")
    args = parser.parse_args()
    return update_current_year(args.output, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
