import logging
import threading

import streamlit as st
from nepse import Nepse

logger = logging.getLogger(__name__)


@st.cache_resource
def get_nepse_client() -> tuple[Nepse, threading.Lock]:
    client = Nepse()
    client.setTLSVerification(False)
    logger.info("Nepse() client initialised")
    return client, threading.Lock()


def fetch_historical_prices(symbol: str) -> list[dict]:
    try:
        client, lock = get_nepse_client()
        with lock:
            raw = client.getCompanyPriceVolumeHistory(symbol)
        data = raw.get("content", [])
        logger.info(f"getCompanyPriceVolumeHistory({symbol}): {len(data)} rows")
        if not data:
            logger.warning(
                f"getCompanyPriceVolumeHistory({symbol}): empty content. "
                f"Raw keys: {list(raw.keys())}"
            )
        return data
    except Exception:
        logger.error(f"getCompanyPriceVolumeHistory({symbol}) failed", exc_info=True)
        return []


def fetch_live_market() -> list[dict]:
    try:
        client, lock = get_nepse_client()
        with lock:
            data = client.getLiveMarket()
        logger.info(f"getLiveMarket(): {len(data)} stocks")
        if not data:
            logger.warning("getLiveMarket(): empty response")
        return data or []
    except Exception:
        logger.error("getLiveMarket() failed", exc_info=True)
        return []


def fetch_company_list() -> list[dict]:
    try:
        client, lock = get_nepse_client()
        with lock:
            data = client.getCompanyList()
        logger.info(f"getCompanyList(): {len(data)} companies")
        if not data:
            logger.warning("getCompanyList(): empty response")
        return data or []
    except Exception:
        logger.error("getCompanyList() failed", exc_info=True)
        return []


def fetch_gainers() -> list[dict]:
    try:
        client, lock = get_nepse_client()
        with lock:
            data = client.getTopGainers()
        logger.info(f"getTopGainers(): {len(data)} entries")
        return data or []
    except Exception:
        logger.error("getTopGainers() failed", exc_info=True)
        return []


def fetch_losers() -> list[dict]:
    try:
        client, lock = get_nepse_client()
        with lock:
            data = client.getTopLosers()
        logger.info(f"getTopLosers(): {len(data)} entries")
        return data or []
    except Exception:
        logger.error("getTopLosers() failed", exc_info=True)
        return []


def fetch_market_status() -> dict:
    try:
        client, lock = get_nepse_client()
        with lock:
            data = client.isNepseOpen()
        is_open = data.get("isOpen", "UNKNOWN") if isinstance(data, dict) else str(data)
        logger.info(f"isNepseOpen(): {is_open}")
        return data if isinstance(data, dict) else {}
    except Exception:
        logger.error("isNepseOpen() failed", exc_info=True)
        return {}
