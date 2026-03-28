import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent.parent / "data"


def _latest_snapshot_path() -> Path | None:
    if not _DATA_DIR.exists():
        return None
    snapshots = sorted(_DATA_DIR.glob("snapshot_*.json"), reverse=True)
    return snapshots[0] if snapshots else None


def _load_raw() -> dict | None:
    path = _latest_snapshot_path()
    if path is None:
        logger.warning("No snapshot file found in data/")
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        logger.info(f"Loaded snapshot from {path.name} (date: {data.get('date')})")
        return data
    except Exception:
        logger.error(f"Failed to load snapshot from {path}", exc_info=True)
        return None


def load_snapshot(symbol: str) -> list[dict]:
    raw = _load_raw()
    if raw is None:
        return []
    history = raw.get("histories", {})
    rows = history.get(symbol, [])
    if rows:
        logger.info(f"Snapshot fallback: {symbol} → {len(rows)} rows")
    else:
        logger.warning(f"Snapshot fallback: {symbol} not found in snapshot")
    return rows


def load_snapshot_live_market() -> list[dict]:
    raw = _load_raw()
    if raw is None:
        return []
    return raw.get("live_market", [])


def load_snapshot_company_list() -> list[dict]:
    raw = _load_raw()
    if raw is None:
        return []
    return raw.get("company_list", [])


def load_snapshot_gainers() -> list[dict]:
    raw = _load_raw()
    if raw is None:
        return []
    return raw.get("gainers", [])


def load_snapshot_losers() -> list[dict]:
    raw = _load_raw()
    if raw is None:
        return []
    return raw.get("losers", [])


def load_snapshot_market_status() -> dict:
    raw = _load_raw()
    if raw is None:
        return {}
    return raw.get("market_status", {})


def snapshot_date() -> str | None:
    raw = _load_raw()
    return raw.get("date") if raw else None
