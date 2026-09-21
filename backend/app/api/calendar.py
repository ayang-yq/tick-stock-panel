"""财报日历 API — 读取 toolbox earnings_calendar.py 落盘的预约披露+业绩预告。"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

import polars as pl
from fastapi import APIRouter, Query, Request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/calendar", tags=["calendar"])

_CACHE: dict = {"df": pl.DataFrame(), "mtime": 0.0}


def _load(data_dir: Path) -> pl.DataFrame:
    path = data_dir / "calendar" / "earnings_calendar.parquet"
    if not path.exists():
        return pl.DataFrame()
    mtime = path.stat().st_mtime
    if _CACHE["df"].is_empty() or mtime != _CACHE["mtime"]:
        try:
            _CACHE["df"] = pl.read_parquet(path)
            _CACHE["mtime"] = mtime
        except Exception as e:  # noqa: BLE001
            logger.warning("read earnings_calendar.parquet failed: %s", e)
            return pl.DataFrame()
    return _CACHE["df"]


@router.get("/earnings")
def earnings(
    request: Request,
    days: int = Query(30, ge=1, le=365),
    symbol: str | None = None,
    include_published: bool = False,
):
    """财报日历: 未来 days 天内预约披露的股票(+已出预告的归母数值)。

    include_published=true 时附带最近一个报告期已披露股票(带预告数据)。
    """
    df = _load(request.app.state.repo.store.data_dir)
    if df.is_empty():
        return {"available": False, "rows": []}
    today = datetime.now(timezone(timedelta(hours=8))).date()
    until = (today + timedelta(days=days)).isoformat()

    if symbol:
        sub = df.filter(pl.col("symbol") == symbol)
    else:
        sub = df.filter(
            pl.col("appoint_date").is_not_null()
            & (pl.col("appoint_date") >= today.isoformat())
            & (pl.col("appoint_date") <= until)
        )
        if include_published:
            past_pub = df.filter(
                pl.col("is_published") & pl.col("forecast_np").is_not_null()
            )
            sub = pl.concat([sub, past_pub], how="diagonal_relaxed").unique(
                subset=["symbol", "report_period"], keep="first"
            )
    sub = sub.sort("appoint_date")
    return {
        "available": True,
        "as_of": today.isoformat(),
        "rows": sub.to_dicts(),
    }
