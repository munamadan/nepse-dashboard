"""
Day 1 API validation — run locally only, never deployed.
Logs raw field names and response shape for every endpoint.
Run: .venv/bin/python validate_api.py
Output saved to: validate_api_output.txt
"""
import json
import logging
import sys
import time
from pathlib import Path

LOG_FILE = "validate_api_output.txt"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, mode="w"),
    ],
)
logger = logging.getLogger("day1_validation")


def safe_call(label: str, fn, *args):
    """Call fn(*args). Log result shape or full traceback. Never crashes."""
    logger.info("=" * 60)
    logger.info(f"Calling: {label}")
    t0 = time.time()
    try:
        result = fn(*args)
        elapsed = time.time() - t0

        if isinstance(result, list):
            logger.info(f"  → list with {len(result)} items in {elapsed:.2f}s")
            if result:
                logger.info(f"  → field names: {list(result[0].keys())}")
                logger.info(f"  → first row:\n{json.dumps(result[0], default=str, indent=4)}")
            else:
                logger.warning(f"  → EMPTY LIST — unexpected for {label}")
        elif isinstance(result, dict):
            logger.info(f"  → dict keys: {list(result.keys())} in {elapsed:.2f}s")
            logger.info(f"  → full response:\n{json.dumps(result, default=str, indent=4)}")
        elif isinstance(result, bool):
            logger.info(f"  → bool: {result} in {elapsed:.2f}s")
        else:
            logger.info(f"  → type {type(result).__name__}: {result} in {elapsed:.2f}s")

        return result
    except Exception:
        logger.error(f"  → FAILED after {time.time()-t0:.2f}s", exc_info=True)
        return None


def check_depth(data: list | None, label: str) -> None:
    if not data:
        logger.warning(f"{label}: no data — cannot check depth")
        return
    logger.info(f"{label}: {len(data)} rows total")
    if len(data) < 90:
        logger.warning(
            f"{label}: only {len(data)} rows — date range selectors must be "
            f"capped to {len(data)} days max. Update the plan before Day 2."
        )

    date_key = next((k for k in ("businessDate", "date", "Date") if k in data[0]), None)
    if date_key:
        logger.info(f"{label}: date field is '{date_key}' | range: {data[0][date_key]} → {data[-1][date_key]}")
    else:
        logger.warning(
            f"{label}: no recognised date field in first row. "
            f"Available keys: {list(data[0].keys())}"
        )


def check_sectors(companies: list | None) -> None:
    if not companies:
        logger.warning("Company list empty — cannot verify sector mapping")
        return

    first = companies[0]
    sector_key = next((k for k in ("sectorName", "sector", "Sector") if k in first), None)
    if not sector_key:
        logger.error(
            f"CRITICAL: no sectorName field in company data. "
            f"Keys present: {list(first.keys())}. "
            "The entire sector chart architecture depends on this field. "
            "The plan needs revision before Day 2."
        )
        return

    logger.info(f"Sector field name confirmed: '{sector_key}'")
    sectors = sorted({c.get(sector_key, "MISSING") for c in companies})
    logger.info(f"Distinct sector values ({len(sectors)}):")
    for s in sectors:
        count = sum(1 for c in companies if c.get(sector_key) == s)
        logger.info(f"  · {s} ({count} stocks)")

    sym_key = next((k for k in ("symbol", "Symbol", "ticker") if k in first), None)
    if sym_key:
        symbols = [c[sym_key] for c in companies]
        if "GBIME" in symbols:
            logger.info("GBIME confirmed in company list.")
        else:
            logger.warning(
                f"GBIME NOT found. Sample symbols: {symbols[:10]}"
            )
    else:
        logger.warning(f"No symbol field found. Keys: {list(first.keys())}")


def main() -> None:
    logger.info("Day 1 API validation started")
    logger.info(f"Output will be saved to: {Path(LOG_FILE).resolve()}")

    logger.info("=" * 60)
    logger.info("Initialising Nepse() client...")
    try:
        from nepse import Nepse
        nepse = Nepse()
        nepse.setTLSVerification(False)
        logger.info("Nepse() ready. TLS verification disabled (expected — NEPSE cert chain issue).")
    except ImportError:
        logger.error(
            "Cannot import Nepse. Activate venv first: source .venv/bin/activate",
            exc_info=True,
        )
        sys.exit(1)
    except Exception:
        logger.error("Nepse() init failed", exc_info=True)
        sys.exit(1)

    # 1. Historical price
    gbime = safe_call("getDailyScripPriceGraph('GBIME')", nepse.getDailyScripPriceGraph, "GBIME")
    check_depth(gbime, "GBIME")

    # 2. NEPSE index history
    idx = safe_call("getDailyNepseIndexGraph()", nepse.getDailyNepseIndexGraph)
    check_depth(idx, "NEPSE_INDEX")

    # 3. Live market
    live = safe_call("getLiveMarket()", nepse.getLiveMarket)
    if live:
        logger.info(f"Live market: {len(live)} stocks")
        sym_key = next((k for k in ("symbol", "Symbol") if k in live[0]), None)
        if sym_key:
            gbime_live = [r for r in live if r.get(sym_key) == "GBIME"]
            if gbime_live:
                logger.info(f"GBIME live row:\n{json.dumps(gbime_live[0], default=str, indent=4)}")
            else:
                logger.warning(f"GBIME not in live market. Sample: {[r.get(sym_key) for r in live[:5]]}")

    # 4. Sub-indices (current only)
    sub = safe_call("getNepseSubIndices()", nepse.getNepseSubIndices)
    if sub:
        logger.info("CONFIRMED: getNepseSubIndices() is current-only. Cannot use for historical line.")

    # 5. Company list + sector check
    companies = safe_call("getCompanyList()", nepse.getCompanyList)
    check_sectors(companies)

    # 6. Gainers / Losers
    safe_call("getTopGainers()", nepse.getTopGainers)
    safe_call("getTopLosers()", nepse.getTopLosers)

    # 7. Market status
    safe_call("isNepseOpen()", nepse.isNepseOpen)

    logger.info("=" * 60)
    logger.info("Validation complete.")
    logger.info(f"Full output: {Path(LOG_FILE).resolve()}")
    logger.info("Before Day 2, check:")
    logger.info("  1. All field names — they define transforms.py variable names")
    logger.info("  2. Historical depth — if <90 days, cap date range selectors")
    logger.info("  3. sectorName values — must match the sector mapping in the plan")


if __name__ == "__main__":
    main()
