import logging
import threading

import streamlit as st
from NepseUnofficialApi import Nepse

from src.data.snapshot import (
    load_snapshot,
    get_snapshot_live_market,
    get_snapshot_company_list,
    get_snapshot_gainers,
    get_snapshot_losers,
    get_snapshot_market_status,
)

logger = logging.getLogger(__name__)

_snapshot_fallback_triggered: bool = False


def was_snapshot_used() -> bool:
    return _snapshot_fallback_triggered


@st.cache_resource
def get_nepse_client() -> tuple[Nepse, threading.Lock]:
    client = Nepse()
    client.setTLSVerification(False)
    return client, threading.Lock()


def fetch_historical_prices(symbol: str) -> list[dict]:
    global _snapshot_fallback_triggered
    try:
        client, lock = get_nepse_client()
        with lock:
            raw = client.getCompanyPriceVolumeHistory(symbol)
        data = raw.get("content", []) if isinstance(raw, dict) else raw
        logger.info(f"getCompanyPriceVolumeHistory({symbol}): {len(data)} rows")
        if not data:
            logger.warning(f"getCompanyPriceVolumeHistory({symbol}): empty response")
        return data or []
    except Exception:
        logger.error(f"getCompanyPriceVolumeHistory({symbol}) failed", exc_info=True)
        _snapshot_fallback_triggered = True
        return load_snapshot(symbol)


def fetch_live_market() -> list[dict]:
    global _snapshot_fallback_triggered
    try:
        client, lock = get_nepse_client()
        with lock:
            raw = client.getLiveMarket()
        data = raw if isinstance(raw, list) else []
        logger.info(f"getLiveMarket(): {len(data)} rows")
        if not data:
            logger.warning("getLiveMarket(): empty response")
        return data or []
    except Exception:
        logger.error("getLiveMarket() failed", exc_info=True)
        _snapshot_fallback_triggered = True
        return get_snapshot_live_market()


def fetch_company_list() -> list[dict]:
    global _snapshot_fallback_triggered
    try:
        client, lock = get_nepse_client()
        with lock:
            raw = client.getCompanyList()
        data = raw if isinstance(raw, list) else []
        logger.info(f"getCompanyList(): {len(data)} companies")
        if not data:
            logger.warning("getCompanyList(): empty response")
        return data or []
    except Exception:
        logger.error("getCompanyList() failed", exc_info=True)
        _snapshot_fallback_triggered = True
        return get_snapshot_company_list()


def fetch_gainers() -> list[dict]:
    global _snapshot_fallback_triggered
    try:
        client, lock = get_nepse_client()
        with lock:
            raw = client.getTopGainers()
        data = raw if isinstance(raw, list) else []
        logger.info(f"getTopGainers(): {len(data)} rows")
        return data or []
    except Exception:
        logger.error("getTopGainers() failed", exc_info=True)
        _snapshot_fallback_triggered = True
        return get_snapshot_gainers()


def fetch_losers() -> list[dict]:
    global _snapshot_fallback_triggered
    try:
        client, lock = get_nepse_client()
        with lock:
            raw = client.getTopLosers()
        data = raw if isinstance(raw, list) else []
        logger.info(f"getTopLosers(): {len(data)} rows")
        return data or []
    except Exception:
        logger.error("getTopLosers() failed", exc_info=True)
        _snapshot_fallback_triggered = True
        return get_snapshot_losers()


def fetch_market_status() -> dict:
    global _snapshot_fallback_triggered
    try:
        client, lock = get_nepse_client()
        with lock:
            raw = client.isNepseOpen()
        logger.info(f"isNepseOpen(): {raw}")
        return raw if isinstance(raw, dict) else {}
    except Exception:
        logger.error("isNepseOpen() failed", exc_info=True)
        _snapshot_fallback_triggered = True
        return get_snapshot_market_status()
