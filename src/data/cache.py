import logging

import pandas as pd
import streamlit as st

from src.data.nepse_client import (
    fetch_historical_prices,
    fetch_live_market,
    fetch_company_list,
    fetch_gainers,
    fetch_losers,
    fetch_market_status,
)
from src.processing.transforms import build_clean_series

logger = logging.getLogger(__name__)

SECTOR_STOCK_CAP = 15


@st.cache_data(ttl=86400)
def get_company_list() -> list[dict]:
    return fetch_company_list()


@st.cache_data(ttl=3600)
def get_historical_prices(symbol: str) -> list[dict]:
    return fetch_historical_prices(symbol)


@st.cache_data(ttl=300)
def get_live_market() -> list[dict]:
    return fetch_live_market()


@st.cache_data(ttl=300)
def get_gainers() -> list[dict]:
    return fetch_gainers()


@st.cache_data(ttl=300)
def get_losers() -> list[dict]:
    return fetch_losers()


@st.cache_data(ttl=300)
def get_market_status() -> dict:
    return fetch_market_status()


def get_sector_symbols(sector_name: str) -> list[str]:
    companies = get_company_list()
    return [
        c["symbol"]
        for c in companies
        if c.get("sectorName") == sector_name and c.get("symbol")
    ]


def get_sector_for_symbol(symbol: str) -> str:
    companies = get_company_list()
    for c in companies:
        if c.get("symbol") == symbol:
            return c.get("sectorName", "")
    return ""


@st.cache_data(ttl=3600)
def get_sector_proxy(sector_name: str) -> pd.Series:
    sector_syms = get_sector_symbols(sector_name)
    if not sector_syms:
        logger.warning(f"get_sector_proxy({sector_name}): no symbols found")
        return pd.Series(dtype=float)

    live = get_live_market()
    volume_map = {row["symbol"]: row.get("totalTradeQuantity", 0) for row in live}
    sorted_syms = sorted(sector_syms, key=lambda s: volume_map.get(s, 0), reverse=True)
    top_syms = sorted_syms[:SECTOR_STOCK_CAP]

    logger.info(f"get_sector_proxy({sector_name}): fetching {len(top_syms)} stocks")

    series_map: dict[str, pd.Series] = {}
    for sym in top_syms:
        raw = fetch_historical_prices(sym)
        if not raw:
            logger.warning(f"get_sector_proxy: no raw data for {sym}, skipping")
            continue
        df = build_clean_series(raw, sym)
        if df.empty:
            logger.warning(f"get_sector_proxy: empty clean series for {sym}, skipping")
            continue
        close = df.set_index("date")["close"]
        if close.iloc[0] == 0:
            logger.warning(f"get_sector_proxy: zero first price for {sym}, skipping")
            continue
        normalized = (close / close.iloc[0]) * 100
        series_map[sym] = normalized

    if not series_map:
        logger.warning(f"get_sector_proxy({sector_name}): no usable series after filtering")
        return pd.Series(dtype=float)

    proxy_df = pd.concat(series_map.values(), axis=1, join="inner")
    proxy = proxy_df.mean(axis=1)
    logger.info(
        f"get_sector_proxy({sector_name}): proxy built from "
        f"{len(series_map)} stocks, {len(proxy)} rows"
    )
    return proxy
