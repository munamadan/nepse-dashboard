import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import logging
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from src.data.cache import get_historical_prices, get_company_list
from src.processing.transforms import (
    normalize_to_index,
    build_clean_series,
    slice_to_days,
    detect_corporate_actions,
    align_multiple_stocks,
)
from src.ui.charts import build_price_chart, build_comparison_chart
from src.ui.panels import render_live_panel, render_gainers_losers
from src.ui.export import build_excel_export

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="NEPSE Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st_autorefresh(interval=300_000, key="live_refresh")

if "selected_symbol" not in st.session_state:
    st.session_state.selected_symbol = "GBIME"
if "comparison_symbols" not in st.session_state:
    st.session_state.comparison_symbols = []
if "date_range_days" not in st.session_state:
    st.session_state.date_range_days = 180

companies = get_company_list()
if companies:
    symbol_to_name: dict[str, str] = {
        c["symbol"]: c["companyName"]
        for c in companies
        if c.get("symbol")
    }
    all_symbols: list[str] = sorted(symbol_to_name.keys())
else:
    logger.warning("company list empty — falling back to GBIME only")
    symbol_to_name = {"GBIME": "Global IME Bank"}
    all_symbols = ["GBIME"]

with st.sidebar:
    st.title("📈 NEPSE Dashboard")
    st.caption("Nepal Stock Exchange · Live + Historical")
    st.divider()

    try:
        stock_idx = all_symbols.index(st.session_state.selected_symbol)
    except ValueError:
        stock_idx = all_symbols.index("GBIME") if "GBIME" in all_symbols else 0

    symbol: str = st.selectbox(
        "Stock",
        options=all_symbols,
        index=stock_idx,
        format_func=lambda s: f"{s} — {symbol_to_name.get(s, s)}",
    )
    st.session_state.selected_symbol = symbol

    _range_opts = [30, 60, 90, 180]
    _range_idx = (
        _range_opts.index(st.session_state.date_range_days)
        if st.session_state.date_range_days in _range_opts
        else 3
    )
    date_range_days: int = st.selectbox(
        "Date Range",
        options=_range_opts,
        index=_range_idx,
        format_func=lambda d: f"{d} days",
    )
    st.session_state.date_range_days = date_range_days

    other_symbols = [s for s in all_symbols if s != symbol]
    valid_defaults = [s for s in st.session_state.comparison_symbols if s in other_symbols]
    comparison_symbols: list[str] = st.multiselect(
        "Compare With (up to 8)",
        options=other_symbols,
        default=valid_defaults,
        max_selections=8,
    )
    st.session_state.comparison_symbols = comparison_symbols

    st.divider()
    st.caption("Source: nepalstock.com · Unofficial API")
    st.caption("Refreshes every 5 min · Historical cache: 1h")

days = st.session_state.date_range_days

st.header(f"{symbol} — {symbol_to_name.get(symbol, '')}")

render_live_panel(symbol)

st.divider()

st.subheader(f"Price History · {days} Days")

with st.spinner("Loading price data..."):
    raw_prices = get_historical_prices(symbol)

if not raw_prices:
    st.warning(f"Could not load price data for {symbol}. Try refreshing.")
    st.stop()

df_full = build_clean_series(raw_prices, symbol)
if df_full.empty:
    st.warning(f"No usable price data for {symbol}. Try refreshing.")
    st.stop()

df = slice_to_days(df_full, days)
if df.empty:
    st.warning(f"No data in the selected {days}-day window for {symbol}.")
    st.stop()

corp_dates = detect_corporate_actions(df)
fig_price = build_price_chart(df, symbol, corp_dates)
st.plotly_chart(fig_price, use_container_width=True)

st.divider()

if comparison_symbols:
    st.subheader(f"Cumulative Return Comparison · {days} Days · Normalized to 100")

    all_comp = [symbol] + comparison_symbols
    with st.spinner(f"Loading {len(all_comp)} stocks for comparison..."):
        series_map: dict = {}
        for sym in all_comp:
            r = get_historical_prices(sym)
            if r:
                d = build_clean_series(r, sym)
                if not d.empty:
                    series_map[sym] = d["close"]
                else:
                    logger.warning("comparison: empty df for %s", sym)
            else:
                logger.warning("comparison: no raw data for %s", sym)

    if len(series_map) < 2:
        st.warning("Not enough data to compare. Try different stocks or a longer date range.")
    else:
        aligned = align_multiple_stocks(series_map)
        if not aligned.empty:
            aligned = slice_to_days(aligned, days)
            aligned = aligned.apply(lambda s: (s / s.iloc[0]) * 100)
        if aligned.empty:
            st.warning("Could not align stocks over the selected period. Try a longer date range.")
        else:
            fig_comp = build_comparison_chart(aligned)
            st.plotly_chart(fig_comp, use_container_width=True)

    st.divider()

st.subheader("Export")
col_btn, col_dl, _ = st.columns([1, 2, 3])

with col_btn:
    if st.button("Prepare Excel Export", type="secondary"):
        with st.spinner("Building Excel file..."):
            export_bytes = build_excel_export(df, symbol, days)
        if export_bytes:
            st.session_state.export_bytes = export_bytes
            st.session_state.export_symbol = symbol
            st.session_state.export_days = days
        else:
            st.error("Export failed — check logs.")

export_ready = (
    "export_bytes" in st.session_state
    and st.session_state.export_bytes
    and st.session_state.get("export_symbol") == symbol
)
if export_ready:
    _exp_days = st.session_state.get("export_days", days)
    _fname = f"{symbol}_{_exp_days}d_analysis.xlsx"
    with col_dl:
        st.download_button(
            label=f"⬇ Download {_fname}",
            data=st.session_state.export_bytes,
            file_name=_fname,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

st.divider()

render_gainers_losers()
