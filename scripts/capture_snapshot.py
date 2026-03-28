import json
import logging
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.nepse_client import (
    fetch_company_list,
    fetch_gainers,
    fetch_historical_prices,
    fetch_live_market,
    fetch_losers,
    fetch_market_status,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

TOP_N = 30


def capture() -> None:
    logger.info("Starting snapshot capture")

    live = fetch_live_market()
    companies = fetch_company_list()
    gainers = fetch_gainers()
    losers = fetch_losers()
    status = fetch_market_status()

    by_volume: list[dict] = sorted(
        [r for r in live if r.get("totalTradeQuantity", 0) > 0],
        key=lambda r: r.get("totalTradeQuantity", 0),
        reverse=True,
    )
    top_symbols: list[str] = [r["symbol"] for r in by_volume[:TOP_N]]

    always_include = ["GBIME", "NABIL", "HBL", "SCB", "NICA"]
    for sym in always_include:
        if sym not in top_symbols:
            top_symbols.append(sym)

    logger.info(f"Capturing history for {len(top_symbols)} symbols: {top_symbols}")

    histories: dict[str, list[dict]] = {}
    for sym in top_symbols:
        rows = fetch_historical_prices(sym)
        if rows:
            histories[sym] = rows
            logger.info(f"  {sym}: {len(rows)} rows captured")
        else:
            logger.warning(f"  {sym}: no data — skipping")

    snapshot = {
        "date": str(date.today()),
        "live_market": live,
        "company_list": companies,
        "gainers": gainers,
        "losers": losers,
        "market_status": status,
        "histories": histories,
    }

    output_dir = Path(__file__).parent.parent / "data"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / f"snapshot_{date.today()}.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)

    logger.info(f"Snapshot written to {output_path} ({output_path.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    capture()
