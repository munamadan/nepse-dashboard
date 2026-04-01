"""
Day 2 pipeline validation — run locally, not part of the app.
Run with: python test_pipeline.py
"""
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("test_pipeline_output.txt", mode="w"),
    ],
)
logger = logging.getLogger("test_pipeline")

from nepse import Nepse
from src.processing.transforms import (
    align_multiple_stocks,
    build_clean_series,
    compute_summary_stats,
    detect_corporate_actions,
    normalize_to_index,
    slice_to_days,
)


def make_client() -> Nepse:
    client = Nepse()
    client.setTLSVerification(False)
    return client


def fetch_raw(client: Nepse, symbol: str) -> list[dict]:
    raw = client.getCompanyPriceVolumeHistory(symbol)
    return raw.get("content", [])


def section(title: str) -> None:
    logger.info("=" * 60)
    logger.info(title)
    logger.info("=" * 60)


def main() -> None:
    client = make_client()

    section("1. build_clean_series(GBIME)")
    raw = fetch_raw(client, "GBIME")
    logger.info(f"Raw rows from API: {len(raw)}")
    logger.info(f"Raw[0] (newest): {raw[0]}")
    logger.info(f"Raw[-1] (oldest): {raw[-1]}")

    df = build_clean_series(raw, "GBIME")

    if df.empty:
        logger.error("build_clean_series returned empty — pipeline broken")
        sys.exit(1)

    logger.info(f"Shape: {df.shape} | Columns: {df.columns.tolist()}")
    logger.info(f"Date range: {df.index.min().date()} → {df.index.max().date()}")
    logger.info(f"Head:\n{df.head(3)}")
    logger.info(f"Tail:\n{df.tail(3)}")
    logger.info(f"Nulls:\n{df.isnull().sum()}")

    section("2. normalize_to_index")
    normed = normalize_to_index(df)
    logger.info(f"First value (must be exactly 100.0): {normed.iloc[0]}")
    logger.info(f"Last value: {normed.iloc[-1]:.4f}")
    assert normed.iloc[0] == 100.0, f"FAIL: first={normed.iloc[0]}, expected 100.0"
    logger.info("PASS: starts at exactly 100.0")

    section("3. slice_to_days(90)")
    sliced = slice_to_days(df, 90)
    normed_sliced = normalize_to_index(sliced)
    assert normed_sliced.iloc[0] == 100.0, "FAIL: sliced normalization broken"
    logger.info(f"PASS: {len(sliced)} rows, starts at 100.0")

    section("4. detect_corporate_actions")
    suspicious = detect_corporate_actions(df)
    logger.info(f"Potential corporate action dates: {len(suspicious)}")
    if not suspicious.empty:
        logger.info(f"\n{suspicious}")

    section("5. compute_summary_stats")
    zero_vol = sum(1 for r in raw if (r.get("totalTradedQuantity") or 0) == 0)
    stats = compute_summary_stats(sliced, zero_volume_days=zero_vol)
    for k, v in stats.items():
        logger.info(f"  {k}: {v}")

    section("6. align_multiple_stocks(GBIME, NABIL)")
    raw_nabil = fetch_raw(client, "NABIL")
    df_nabil = build_clean_series(raw_nabil, "NABIL")
    aligned = align_multiple_stocks({
        "GBIME": normalize_to_index(df),
        "NABIL": normalize_to_index(df_nabil),
    })
    logger.info(f"Aligned shape: {aligned.shape}")
    logger.info(f"GBIME first: {aligned['GBIME'].iloc[0]:.4f}, NABIL first: {aligned['NABIL'].iloc[0]:.4f}")

    section("7. Sector proxy timing — top 5 Commercial Banks")
    live = client.getLiveMarket()
    companies = client.getCompanyList()

    bank_symbols = [c["symbol"] for c in companies if c.get("sectorName") == "Commercial Banks"]
    volume_map = {r["symbol"]: r.get("totalTradeQuantity", 0) for r in live}
    bank_symbols.sort(key=lambda s: volume_map.get(s, 0), reverse=True)
    test_symbols = bank_symbols[:5]
    logger.info(f"Testing with: {test_symbols}")

    t0 = time.time()
    sector_series = {}
    for sym in test_symbols:
        sym_df = build_clean_series(fetch_raw(client, sym), sym)
        if not sym_df.empty:
            sector_series[sym] = normalize_to_index(sym_df)
        logger.info(f"  {sym}: done ({time.time() - t0:.1f}s elapsed)")

    elapsed_5 = time.time() - t0
    projected_15 = elapsed_5 / 5 * 15

    logger.info(f"5 stocks in {elapsed_5:.2f}s → projected 15 stocks: {projected_15:.1f}s")

    if projected_15 < 30:
        logger.info("DECISION: sector reconstruction is fast enough — use primary implementation")
    else:
        logger.warning(
            f"DECISION: {projected_15:.0f}s projected for 15 stocks — use peer-picker fallback"
        )

    if len(sector_series) >= 2:
        proxy = align_multiple_stocks(sector_series).mean(axis=1)
        logger.info(f"Sector proxy first value: {proxy.iloc[0]:.4f} (expect ~100.0)")
        assert abs(proxy.iloc[0] - 100.0) < 0.01, "FAIL: sector proxy not starting at 100"
        logger.info("PASS: sector proxy starts at 100.0")

    section("ALL CHECKS PASSED")
    logger.info("Pipeline is working. Output saved to test_pipeline_output.txt")
    logger.info(
        f"Sector timing verdict: 5 stocks={elapsed_5:.1f}s, "
        f"15 stocks≈{projected_15:.0f}s → "
        f"{'PRIMARY' if projected_15 < 30 else 'PEER-PICKER FALLBACK'}"
    )


if __name__ == "__main__":
    main()
