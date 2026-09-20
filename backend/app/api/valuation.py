"""估值分位 API — 读取 toolbox 计算引擎落盘的 valuation.parquet。"""
from __future__ import annotations

import logging
from pathlib import Path

import polars as pl
from fastapi import APIRouter, Request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/valuation", tags=["valuation"])

_CACHE: dict = {"df": pl.DataFrame(), "mtime": 0.0}


def _load(data_dir: Path) -> pl.DataFrame:
    path = data_dir / "valuation" / "valuation.parquet"
    if not path.exists():
        return pl.DataFrame()
    mtime = path.stat().st_mtime
    if _CACHE["df"].is_empty() or mtime != _CACHE["mtime"]:
        try:
            _CACHE["df"] = pl.read_parquet(path)
            _CACHE["mtime"] = mtime
        except Exception as e:  # noqa: BLE001
            logger.warning("read valuation.parquet failed: %s", e)
            return pl.DataFrame()
    return _CACHE["df"]


@router.get("/snapshot")
def snapshot(request: Request, symbol: str | None = None):
    """估值截面: 全市场或单股。列: pe_ttm/pb/pct_1y/pct_3y/pct_5y/eps_period/as_of。"""
    df = _load(request.app.state.repo.store.data_dir)
    if df.is_empty():
        return {"available": False, "rows": []}
    if symbol:
        df = df.filter(pl.col("symbol") == symbol)
    return {
        "available": True,
        "as_of": df["as_of"][0] if df.height else None,
        "rows": df.to_dicts(),
    }
