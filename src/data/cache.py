# INVARIANT: cached functions take only symbol: str or no args — never date ranges.
# Date slicing happens in the UI layer only. Every unique argument combination
# creates a separate cache entry; passing date ranges would exhaust shared memory.

import logging

import pandas as pd
import streamlit as st

from src.data.nepse_client import (
    fetch_company_list,
    fetch_gainers,
    fetch_historical_prices,
    fetch_live_market,
    fetch_losers,
    fetch_market_status,
)
from src.processing.transforms import (
    align_multiple_stocks,
    build_clean_series,
    normalize_to_index,
)

logger = logging.getLogger(__name__)

SECTOR_STOCK_CAP = 15


@st.cache_data(ttl=3600)
def get_historical_prices(symbol: str) -> list[dict]:
    logger.info(f"Cache miss: get_historical_prices({symbol})")
    return fetch_historical_prices(symbol)


@st.cache_data(ttl=300)
def get_live_market() -> list[dict]:
    logger.info("Cache miss: get_live_market()")
    return fetch_live_market()


@st.cache_data(ttl=86400)
def get_company_list() -> list[dict]:
    logger.info("Cache miss: get_company_list()")
    return fetch_company_list()


@st.cache_data(ttl=300)
def get_gainers() -> list[dict]:
    logger.info("Cache miss: get_gainers()")
    return fetch_gainers()


@st.cache_data(ttl=300)
def get_losers() -> list[dict]:
    logger.info("Cache miss: get_losers()")
    return fetch_losers()


@st.cache_data(ttl=300)
def get_market_status() -> dict:
    logger.info("Cache miss: get_market_status()")
    return fetch_market_status()


def get_sector_symbols(sector_name: str) -> list[str]:
    companies = get_company_list()
    symbols = [c["symbol"] for c in companies if c.get("sectorName") == sector_name]
    logger.info(f"Sector '{sector_name}': {len(symbols)} listed stocks")
    return symbols


@st.cache_data(ttl=3600)
def get_sector_proxy(sector_name: str) -> pd.Series:
    logger.info(f"Cache miss: get_sector_proxy({sector_name})")

    sector_symbols = get_sector_symbols(sector_name)
    if not sector_symbols:
        logger.warning(f"get_sector_proxy({sector_name}): no symbols found")
        return pd.Series(dtype=float)

    live = get_live_market()
    volume_map: dict[str, float] = {
        r["symbol"]: r.get("totalTradeQuantity", 0) for r in live
    }

    sector_symbols.sort(key=lambda s: volume_map.get(s, 0), reverse=True)
    selected = sector_symbols[:SECTOR_STOCK_CAP]
    logger.info(
        f"get_sector_proxy({sector_name}): using top {len(selected)} stocks "
        f"by live volume: {selected}"
    )

    series_dict: dict[str, pd.Series] = {}
    for sym in selected:
        raw = get_historical_prices(sym)
        df = build_clean_series(raw, sym)
        if not df.empty:
            series_dict[sym] = normalize_to_index(df)
        else:
            logger.warning(f"get_sector_proxy: skipping {sym} — empty after cleaning")

    if not series_dict:
        logger.warning(f"get_sector_proxy({sector_name}): all fetches returned empty")
        return pd.Series(dtype=float)

    logger.info(
        f"get_sector_proxy({sector_name}): {len(series_dict)}/{len(selected)} "
        "stocks contributed data"
    )
    aligned = align_multiple_stocks(series_dict)
    return aligned.mean(axis=1)
