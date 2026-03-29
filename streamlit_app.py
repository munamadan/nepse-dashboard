import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

st.set_page_config(
    page_title="NEPSE Dashboard",
    page_icon="📈",
    layout="wide",
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

from streamlit_autorefresh import st_autorefresh

from src.data.cache import get_company_list
from src.ui.panels import render_gainers_losers, render_live_panel

st_autorefresh(interval=300_000, key="live_refresh")

if "selected_symbol" not in st.session_state:
    st.session_state.selected_symbol = "GBIME"
if "comparison_symbols" not in st.session_state:
    st.session_state.comparison_symbols = []
if "date_range_days" not in st.session_state:
    st.session_state.date_range_days = 180
if "initialized" not in st.session_state:
    st.session_state.initialized = True

with st.sidebar:
    st.title("NEPSE Dashboard")
    st.markdown("---")

    with st.spinner("Loading company list..."):
        companies = get_company_list()

    if companies:
        symbols = sorted(set(c["symbol"] for c in companies if c.get("symbol")))
        current = st.session_state.selected_symbol
        default_idx = symbols.index(current) if current in symbols else 0

        selected = st.selectbox(
            "Select Stock",
            options=symbols,
            index=default_idx,
            help="Type to search. Default: GBIME (Global IME Bank)",
        )
        st.session_state.selected_symbol = selected
    else:
        st.error("Could not load company list.")
        selected = st.session_state.selected_symbol

    st.markdown("---")
    st.caption("Data: NepseUnofficialApi · Refreshes every 5 min")

symbol = st.session_state.selected_symbol

st.header(f"📊 {symbol} — Live Snapshot")

with st.spinner(f"Fetching live data for {symbol}..."):
    render_live_panel(symbol)

st.divider()

st.header("🏆 Market Movers")
with st.spinner("Loading gainers and losers..."):
    render_gainers_losers(n=5)
