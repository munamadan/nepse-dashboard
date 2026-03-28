import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

from src.ui.charts import (
    build_comparison_chart,
    build_gainers_losers_chart,
    build_price_chart,
    build_sector_chart,
)

OUT = Path("test_charts_output")
OUT.mkdir(exist_ok=True)


def _make_price_df(n: int = 90, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range(end="2026-03-27", periods=n, freq="B")
    close = 400.0 + np.cumsum(rng.normal(0, 5, n))
    high = close + rng.uniform(2, 10, n)
    low = close - rng.uniform(2, 10, n)
    volume = rng.integers(10_000, 200_000, n).astype(float)
    return pd.DataFrame({"close": close, "high": high, "low": low, "volume": volume}, index=dates)


def _make_aligned_df(symbols: list[str], n: int = 90) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    dates = pd.date_range(end="2026-03-27", periods=n, freq="B")
    data = {}
    for i, sym in enumerate(symbols):
        prices = 100.0 + np.cumsum(rng.normal(0, 1.5, n))
        data[sym] = prices
    return pd.DataFrame(data, index=dates)


def _make_series(n: int = 90, seed: int = 0) -> pd.Series:
    rng = np.random.default_rng(seed)
    dates = pd.date_range(end="2026-03-27", periods=n, freq="B")
    values = 100.0 + np.cumsum(rng.normal(0, 1, n))
    return pd.Series(values, index=dates)


def _make_gainers_losers():
    gainers = pd.DataFrame({
        "symbol": ["NABIL", "HBL", "SCB", "EBL", "KBL"],
        "percentageChange": [4.5, 3.8, 3.1, 2.9, 2.4],
    })
    losers = pd.DataFrame({
        "symbol": ["KDBY", "SICL", "RURU", "NHPC", "MFIL"],
        "percentageChange": [-4.9, -4.1, -3.6, -2.8, -2.2],
    })
    return gainers, losers


def test_price_chart():
    logger.info("=== test_price_chart ===")
    df = _make_price_df()
    corp_dates = ["2026-01-15", "2026-02-20"]
    fig = build_price_chart(df, "GBIME", corp_dates)
    assert len(fig.data) == 3, f"Expected 3 traces, got {len(fig.data)}"
    path = OUT / "price_chart.html"
    fig.write_html(str(path))
    logger.info(f"Written: {path}")


def test_price_chart_empty():
    logger.info("=== test_price_chart_empty (should warn, return empty figure) ===")
    fig = build_price_chart(pd.DataFrame(), "XXX", [])
    assert len(fig.data) == 0
    logger.info("Empty figure returned correctly")


def test_comparison_chart():
    logger.info("=== test_comparison_chart ===")
    aligned = _make_aligned_df(["GBIME", "NABIL", "HBL", "EBL"])
    fig = build_comparison_chart(aligned)
    assert len(fig.data) == 4
    path = OUT / "comparison_chart.html"
    fig.write_html(str(path))
    logger.info(f"Written: {path}")


def test_sector_chart():
    logger.info("=== test_sector_chart ===")
    stock = _make_series(90, seed=1)
    sector = _make_series(85, seed=2)
    fig = build_sector_chart(stock, sector, "GBIME")
    assert len(fig.data) == 2
    path = OUT / "sector_chart.html"
    fig.write_html(str(path))
    logger.info(f"Written: {path}")


def test_sector_chart_no_sector():
    logger.info("=== test_sector_chart_no_sector (missing sector series) ===")
    stock = _make_series(90, seed=3)
    fig = build_sector_chart(stock, pd.Series(dtype=float), "GBIME")
    assert len(fig.data) == 1
    logger.info("Single-line sector chart returned correctly")


def test_gainers_losers_chart():
    logger.info("=== test_gainers_losers_chart ===")
    gainers, losers = _make_gainers_losers()
    fig = build_gainers_losers_chart(gainers, losers)
    assert len(fig.data) == 2
    path = OUT / "gainers_losers_chart.html"
    fig.write_html(str(path))
    logger.info(f"Written: {path}")


if __name__ == "__main__":
    test_price_chart()
    test_price_chart_empty()
    test_comparison_chart()
    test_sector_chart()
    test_sector_chart_no_sector()
    test_gainers_losers_chart()
    logger.info(f"\nAll chart tests passed. Open files in {OUT}/ to inspect visually.")
