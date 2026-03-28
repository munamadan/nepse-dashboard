import logging
import threading

import streamlit as st
from nepse import Nepse

logger = logging.getLogger(__name__)


@st.cache_resource
def get_nepse_client() -> tuple[Nepse, threading.Lock]:
    client = Nepse()
    client.setTLSVerification(False)
    logger.info("Nepse client initialised")
    return client, threading.Lock()


def fetch_historical_prices(symbol: str) -> list[dict]:
    try:
        client, lock = get_nepse_client()
        with lock:
            raw = client.getCompanyPriceVolumeHistory(symbol)
        data: list[dict] = raw.get("content", []) if isinstance(raw, dict) else []
        logger.info(f"getCompanyPriceVolumeHistory({symbol}): {len(data)} rows")
        if not data:
            logger.warning(f"getCompanyPriceVolumeHistory({symbol}): empty response")
        return data or []
    except Exception:
        logger.error(f"getCompanyPriceVolumeHistory({symbol}) failed — trying snapshot", exc_info=True)
        from src.data.snapshot import load_snapshot
        return load_snapshot(symbol)


def fetch_live_market() -> list[dict]:
    try:
        client, lock = get_nepse_client()
        with lock:
            raw = client.getLiveMarket()
        data: list[dict] = raw if isinstance(raw, list) else []
        logger.info(f"getLiveMarket(): {len(data)} rows")
        if not data:
            logger.warning("getLiveMarket(): empty response")
        return data or []
    except Exception:
        logger.error("getLiveMarket() failed — trying snapshot", exc_info=True)
        from src.data.snapshot import load_snapshot_live_market
        return load_snapshot_live_market()


def fetch_company_list() -> list[dict]:
    try:
        client, lock = get_nepse_client()
        with lock:
            raw = client.getCompanyList()
        data: list[dict] = raw if isinstance(raw, list) else []
        logger.info(f"getCompanyList(): {len(data)} companies")
        if not data:
            logger.warning("getCompanyList(): empty response")
        return data or []
    except Exception:
        logger.error("getCompanyList() failed — trying snapshot", exc_info=True)
        from src.data.snapshot import load_snapshot_company_list
        return load_snapshot_company_list()


def fetch_gainers() -> list[dict]:
    try:
        client, lock = get_nepse_client()
        with lock:
            raw = client.getTopGainers()
        data: list[dict] = raw if isinstance(raw, list) else []
        logger.info(f"getTopGainers(): {len(data)} rows")
        if not data:
            logger.warning("getTopGainers(): empty response")
        return data or []
    except Exception:
        logger.error("getTopGainers() failed — trying snapshot", exc_info=True)
        from src.data.snapshot import load_snapshot_gainers
        return load_snapshot_gainers()


def fetch_losers() -> list[dict]:
    try:
        client, lock = get_nepse_client()
        with lock:
            raw = client.getTopLosers()
        data: list[dict] = raw if isinstance(raw, list) else []
        logger.info(f"getTopLosers(): {len(data)} rows")
        if not data:
            logger.warning("getTopLosers(): empty response")
        return data or []
    except Exception:
        logger.error("getTopLosers() failed — trying snapshot", exc_info=True)
        from src.data.snapshot import load_snapshot_losers
        return load_snapshot_losers()


def fetch_market_status() -> dict:
    try:
        client, lock = get_nepse_client()
        with lock:
            raw = client.isNepseOpen()
        data: dict = raw if isinstance(raw, dict) else {}
        logger.info(f"isNepseOpen(): {data}")
        return data
    except Exception:
        logger.error("isNepseOpen() failed — trying snapshot", exc_info=True)
        from src.data.snapshot import load_snapshot_market_status
        return load_snapshot_market_status()
