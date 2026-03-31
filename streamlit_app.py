import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from src.data.cache import (
    get_company_list,
    get_historical_prices,
    get_sector_proxy,
    get_sector_for_symbol,
)
from src.data.nepse_client import was_snapshot_used
from src.data.snapshot import snapshot_date
from src.processing.transforms import (
    build_clean_series,
    slice_to_days,
    detect_corporate_actions,
    align_multiple_stocks,
)
from src.ui.charts import (
    build_price_chart,
    build_comparison_chart,
    build_sector_chart,
)
from src.ui.panels import render_live_panel, render_gainers_losers
from src.ui.export import build_excel_export

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

# ── Page config must be first Streamlit call ──────────────────────────────────
st.set_page_config(
    page_title="NEPSE Dashboard",
    page_icon="📈",
    layout="wide",
)

st_autorefresh(interval=300_000, key="live_refresh")

# ── Session state init ────────────────────────────────────────────────────────
if "selected_symbol" not in st.session_state:
    st.session_state.selected_symbol = "GBIME"
if "comparison_symbols" not in st.session_state:
    st.session_state.comparison_symbols = []
if "date_range_days" not in st.session_state:
    st.session_state.date_range_days = 180
if "initialized" not in st.session_state:
    st.session_state.initialized = True

# ── Snapshot fallback banner ──────────────────────────────────────────────────
if was_snapshot_used():
    snap_dt = snapshot_date()
    st.info(
        f"⚠️ Live data unavailable — showing snapshot from {snap_dt}. "
        "Refresh to reconnect."
    )

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("NEPSE Dashboard")
    st.caption("Nepal Stock Exchange · Live Data")

    with st.spinner("Loading company list..."):
        companies = get_company_list()

    symbols = sorted([c["symbol"] for c in companies if c.get("symbol")])
    valid_symbols = set(symbols)

    st.session_state.comparison_symbols = [
        s for s in st.session_state.comparison_symbols if s in valid_symbols
    ]

    default_idx = symbols.index("GBIME") if "GBIME" in symbols else 0
    current_idx = (
        symbols.index(st.session_state.selected_symbol)
        if st.session_state.selected_symbol in symbols
        else default_idx
    )

    st.selectbox(
        "Select Stock",
        options=symbols,
        index=current_idx,
        key="selected_symbol",
    )

    st.radio(
        "Date Range",
        options=[30, 60, 90, 180],
        index=[30, 60, 90, 180].index(st.session_state.date_range_days),
        key="date_range_days",
        horizontal=True,
    )

    other_symbols = [s for s in symbols if s != st.session_state.selected_symbol]
    st.multiselect(
        "Compare with (up to 8)",
        options=other_symbols,
        max_selections=8,
        key="comparison_symbols",
    )

    st.divider()
    st.caption("Data: NepseUnofficialApi · Refreshes every 5 min")

# ── Resolved values ───────────────────────────────────────────────────────────
symbol: str = st.session_state.selected_symbol
date_range_days: int = st.session_state.date_range_days
comparison_symbols: list[str] = st.session_state.comparison_symbols

st.title(f"📈 {symbol} — NEPSE Stock Analysis")

# ── Price History Chart ───────────────────────────────────────────────────────
st.subheader("Price History")

with st.spinner(f"Loading {symbol} price data..."):
    raw = get_historical_prices(symbol)

df = build_clean_series(raw, symbol)
df = slice_to_days(df, date_range_days)

if df.empty:
    st.warning(f"Could not load price data for {symbol}. Try refreshing.")
    st.stop()

corp_dates = detect_corporate_actions(df)
fig_price = build_price_chart(df, symbol, corp_dates)
st.plotly_chart(fig_price, use_container_width=True)

# ── Sector Proxy Chart ────────────────────────────────────────────────────────
st.subheader(f"{symbol} vs Sector Proxy")

sector_name = get_sector_for_symbol(symbol)

if not sector_name:
    st.warning(f"Could not determine sector for {symbol}.")
else:
    with st.spinner(
        f"Computing sector proxy for {sector_name} — fetching up to 15 stocks..."
    ):
        sector_proxy_full = get_sector_proxy(sector_name)

    if sector_proxy_full.empty:
        st.warning(f"Sector proxy unavailable for {sector_name}.")
    else:
        start_date: pd.Timestamp = df["date"].iloc[0]
        sector_sliced = sector_proxy_full[sector_proxy_full.index >= start_date]

        if sector_sliced.empty:
            st.warning("Not enough sector data for the selected date range.")
        else:
            stock_close = df.set_index("date")["close"]
            stock_series = (stock_close / stock_close.iloc[0]) * 100
            sector_series = (sector_sliced / sector_sliced.iloc[0]) * 100

            fig_sector = build_sector_chart(stock_series, sector_series, symbol)
            st.plotly_chart(fig_sector, use_container_width=True)

    st.caption(
        f"Sector: {sector_name} · Equal-weighted mean of top 15 stocks by volume"
    )

# ── Multi-Stock Comparison Chart ──────────────────────────────────────────────
if comparison_symbols:
    st.subheader("Multi-Stock Comparison")

    series_map: dict[str, pd.Series] = {}

    with st.spinner("Loading comparison data..."):
        for sym in [symbol] + list(comparison_symbols):
            raw_sym = get_historical_prices(sym)
            df_sym = build_clean_series(raw_sym, sym)
            if not df_sym.empty:
                series_map[sym] = df_sym.set_index("date")["close"]
            else:
                logger.warning(f"Comparison: empty series for {sym}, skipping")

    if len(series_map) < 2:
        st.warning("Not enough data to build comparison. Try different stocks.")
    else:
        aligned = align_multiple_stocks(series_map)

        if aligned.empty:
            st.warning("No overlapping trading days found for the selected stocks.")
        else:
            if len(aligned) > date_range_days:
                aligned = aligned.iloc[-date_range_days:]

            if len(aligned) < 2:
                st.warning("Not enough overlapping data for the selected date range.")
            else:
                normalized = aligned.apply(lambda s: (s / s.iloc[0]) * 100)
                fig_comp = build_comparison_chart(normalized)
                st.plotly_chart(fig_comp, use_container_width=True)

# ── Excel Export ──────────────────────────────────────────────────────────────
st.subheader("Export Data")

col_btn, col_dl = st.columns([1, 3])

with col_btn:
    if st.button("Prepare Export"):
        with st.spinner("Building Excel file..."):
            st.session_state.export_bytes = build_excel_export(
                df, symbol, date_range_days
            )
            st.session_state.export_symbol = symbol

if (
    "export_bytes" in st.session_state
    and st.session_state.get("export_symbol") == symbol
    and st.session_state.export_bytes
):
    with col_dl:
        st.download_button(
            label=f"⬇️ Download {symbol}_{date_range_days}d.xlsx",
            data=st.session_state.export_bytes,
            file_name=f"{symbol}_{date_range_days}d.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

st.divider()

# ── Live Market Panel + Gainers/Losers ────────────────────────────────────────
render_live_panel(symbol)
st.divider()
render_gainers_losers()
