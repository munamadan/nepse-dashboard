import logging

import pandas as pd
import streamlit as st

from src.data.cache import get_gainers, get_live_market, get_losers, get_market_status
from src.ui.charts import build_gainers_losers_chart

logger = logging.getLogger(__name__)


def render_live_panel(symbol: str) -> None:
    status_data = get_market_status()
    market_data = get_live_market()

    is_open = status_data.get("isOpen") in ("OPEN",) if status_data else False
    as_of = status_data.get("asOf", "N/A") if status_data else "N/A"

    badge = "🟢 Market Open" if is_open else "🔴 Market Closed"
    st.caption(f"{badge} — as of {as_of}")

    stock_row = next((r for r in market_data if r.get("symbol") == symbol), None)

    if not stock_row:
        st.warning(f"No live data found for **{symbol}**. The stock may not have traded today.")
        logger.warning("render_live_panel: no row found for symbol=%s in live market", symbol)
        return

    ltp = stock_row.get("lastTradedPrice") or 0.0
    pct_change = stock_row.get("percentageChange") or 0.0
    open_price = stock_row.get("openPrice") or 0.0
    high = stock_row.get("highPrice") or 0.0
    low = stock_row.get("lowPrice") or 0.0
    prev_close = stock_row.get("previousClose") or 0.0
    volume = stock_row.get("totalTradeQuantity") or 0

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        st.metric(
            label="LTP",
            value=f"Rs {ltp:,.2f}",
            delta=f"{pct_change:+.2f}%",
        )
    with col2:
        st.metric(label="Open", value=f"Rs {open_price:,.2f}")
    with col3:
        st.metric(label="High", value=f"Rs {high:,.2f}")
    with col4:
        st.metric(label="Low", value=f"Rs {low:,.2f}")
    with col5:
        st.metric(label="Prev Close", value=f"Rs {prev_close:,.2f}")
    with col6:
        st.metric(label="Volume", value=f"{int(volume):,}")

    logger.info("render_live_panel: %s LTP=%.2f pct=%.2f%%", symbol, ltp, pct_change)


def render_gainers_losers(n: int = 5) -> None:
    gainers = get_gainers()
    losers = get_losers()

    top_gainers = gainers[:n] if gainers else []
    top_losers = losers[:n] if losers else []

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Top Gainers**")
        if top_gainers:
            df_g = pd.DataFrame(top_gainers)[
                ["symbol", "ltp", "pointChange", "percentageChange"]
            ].rename(
                columns={
                    "symbol": "Symbol",
                    "ltp": "LTP",
                    "pointChange": "Pt Change",
                    "percentageChange": "% Change",
                }
            )
            df_g["% Change"] = df_g["% Change"].map(lambda x: f"+{x:.2f}%")
            df_g["LTP"] = df_g["LTP"].map(lambda x: f"Rs {x:,.2f}")
            st.dataframe(df_g, hide_index=True, use_container_width=True)
        else:
            st.warning("Gainers data unavailable.")

    with col2:
        st.markdown("**Top Losers**")
        if top_losers:
            df_l = pd.DataFrame(top_losers)[
                ["symbol", "ltp", "pointChange", "percentageChange"]
            ].rename(
                columns={
                    "symbol": "Symbol",
                    "ltp": "LTP",
                    "pointChange": "Pt Change",
                    "percentageChange": "% Change",
                }
            )
            df_l["% Change"] = df_l["% Change"].map(lambda x: f"{x:.2f}%")
            df_l["LTP"] = df_l["LTP"].map(lambda x: f"Rs {x:,.2f}")
            st.dataframe(df_l, hide_index=True, use_container_width=True)
        else:
            st.warning("Losers data unavailable.")

    if top_gainers and top_losers:
        fig = build_gainers_losers_chart(pd.DataFrame(top_gainers), pd.DataFrame(top_losers))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
        logger.warning("render_gainers_losers: missing gainers or losers, skipping chart")
