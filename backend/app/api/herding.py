"""抱团度 API — 读取 toolbox 计算引擎落盘的 herding.parquet。

指标: 前5%个股成交额占全市场成交额比例（成交额集中度/抱团度）。
数据由 ~/tsp-toolbox/adapter/herding_calc.py 日更生成（不碰 TSP 源码计算层）。
"""
from __future__ import annotations

import logging
from pathlib import Path

import polars as pl
from fastapi import APIRouter, Request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/herding", tags=["herding"])

_CACHE: dict = {"df": pl.DataFrame(), "mtime": 0.0}


def _load(data_dir: Path) -> pl.DataFrame:
    path = data_dir / "herding" / "herding.parquet"
    if not path.exists():
        return pl.DataFrame()
    mtime = path.stat().st_mtime
    if _CACHE["df"].is_empty() or mtime != _CACHE["mtime"]:
        try:
            _CACHE["df"] = pl.read_parquet(path)
            _CACHE["mtime"] = mtime
        except Exception as e:  # noqa: BLE001
            logger.warning("read herding.parquet failed: %s", e)
            return pl.DataFrame()
    return _CACHE["df"]


@router.get("/history")
def history(request: Request, days: int = 0):
    """抱团度日频序列。days>0 只取最近N天（默认全史）。

    返回: rows[{date,pct,ma20,n,total}] + latest 摘要（当前值/前值/全史分位/均值）。
    """
    df = _load(request.app.state.repo.store.data_dir)
    if df.is_empty():
        return {"available": False, "rows": [], "latest": None}
    if days and days > 0:
        df = df.tail(days)
    full = _CACHE["df"]
    last = df.rows(named=True)[-1]
    prev = df.rows(named=True)[-2] if df.height > 1 else last
    pctile = round((full["pct"] < last["pct"]).sum() / full.height * 100, 1)
    return {
        "available": True,
        "rows": df.to_dicts(),
        "latest": {
            "date": str(last["date"]),
            "pct": last["pct"],
            "prev_pct": prev["pct"],
            "pctile": pctile,
            "mean": round(full["pct"].mean(), 1),
            "n": last["n"],
        },
    }
