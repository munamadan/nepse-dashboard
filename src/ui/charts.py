import logging

import pandas as pd
import plotly.graph_objects as go

logger = logging.getLogger(__name__)

_STOCK_COLOR = "#2563EB"
_SECTOR_COLOR = "#F59E0B"
_GAIN_COLOR = "#16A34A"
_LOSS_COLOR = "#DC2626"

_LAYOUT_DEFAULTS = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, system-ui, sans-serif", size=13),
    margin=dict(l=10, r=10, t=40, b=10),
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    xaxis=dict(showgrid=False, zeroline=False),
    yaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.15)", zeroline=False),
)


def _apply_defaults(fig: go.Figure, title: str) -> go.Figure:
    fig.update_layout(title=dict(text=title, font=dict(size=15)), **_LAYOUT_DEFAULTS)
    return fig


def build_price_chart(
    df: pd.DataFrame,
    symbol: str,
    corporate_action_dates: list[str],
) -> go.Figure:
    if df.empty:
        logger.warning(f"build_price_chart({symbol}): empty dataframe")
        return go.Figure()

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["high"],
            name="High",
            line=dict(color=_STOCK_COLOR, width=1, dash="dot"),
            opacity=0.6,
            hovertemplate="%{y:.2f}",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["low"],
            name="Low",
            line=dict(color=_STOCK_COLOR, width=1, dash="dot"),
            opacity=0.6,
            fill="tonexty",
            fillcolor="rgba(37,99,235,0.07)",
            hovertemplate="%{y:.2f}",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["close"],
            name="Close",
            line=dict(color=_STOCK_COLOR, width=2),
            hovertemplate="%{y:.2f}",
        )
    )

    for date_str in corporate_action_dates:
        fig.add_vline(
            x=pd.Timestamp(date_str).timestamp() * 1000,
            line_dash="dot",
            line_color="orange",
            annotation_text="Corp. action",
            annotation_position="top left",
            annotation_textangle=-90,
            annotation_font_size=10,
        )

    _apply_defaults(fig, f"{symbol} — Price History (High / Low / Close)")
    fig.update_yaxes(title_text="Price (NPR)")
    logger.info(f"build_price_chart({symbol}): {len(df)} rows, {len(corporate_action_dates)} corp actions")
    return fig


def build_comparison_chart(aligned_df: pd.DataFrame) -> go.Figure:
    if aligned_df.empty:
        logger.warning("build_comparison_chart: empty dataframe")
        return go.Figure()

    palette = [
        "#2563EB", "#DC2626", "#16A34A", "#D97706",
        "#7C3AED", "#DB2777", "#0891B2", "#65A30D",
    ]

    fig = go.Figure()

    for i, col in enumerate(aligned_df.columns):
        color = palette[i % len(palette)]
        fig.add_trace(
            go.Scatter(
                x=aligned_df.index,
                y=aligned_df[col],
                name=col,
                line=dict(color=color, width=2),
                hovertemplate=f"{col}: %{{y:.1f}}<extra></extra>",
            )
        )

    fig.add_hline(y=100, line_dash="dash", line_color="rgba(128,128,128,0.4)", line_width=1)

    _apply_defaults(fig, "Multi-Stock Comparison — Cumulative Return (Indexed to 100)")
    fig.update_yaxes(title_text="Indexed Return (start = 100)")
    logger.info(f"build_comparison_chart: {len(aligned_df.columns)} stocks, {len(aligned_df)} rows")
    return fig


def build_sector_chart(
    stock_series: pd.Series,
    sector_series: pd.Series,
    symbol: str,
) -> go.Figure:
    if stock_series.empty:
        logger.warning(f"build_sector_chart({symbol}): empty stock series")
        return go.Figure()

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=stock_series.index,
            y=stock_series.values,
            name=symbol,
            line=dict(color=_STOCK_COLOR, width=2.5),
            hovertemplate=f"{symbol}: %{{y:.1f}}<extra></extra>",
        )
    )

    if not sector_series.empty:
        fig.add_trace(
            go.Scatter(
                x=sector_series.index,
                y=sector_series.values,
                name="Sector Proxy",
                line=dict(color=_SECTOR_COLOR, width=2, dash="dash"),
                hovertemplate="Sector: %{y:.1f}<extra></extra>",
            )
        )

    fig.add_hline(y=100, line_dash="dash", line_color="rgba(128,128,128,0.4)", line_width=1)

    _apply_defaults(fig, f"{symbol} vs Sector Proxy (Indexed to 100)")
    fig.update_yaxes(title_text="Indexed Return (start = 100)")
    logger.info(f"build_sector_chart({symbol}): stock={len(stock_series)} rows, sector={len(sector_series)} rows")
    return fig


def build_gainers_losers_chart(
    gainers_df: pd.DataFrame,
    losers_df: pd.DataFrame,
) -> go.Figure:
    if gainers_df.empty and losers_df.empty:
        logger.warning("build_gainers_losers_chart: both dataframes empty")
        return go.Figure()

    fig = go.Figure()

    if not gainers_df.empty:
        fig.add_trace(
            go.Bar(
                x=gainers_df["percentageChange"],
                y=gainers_df["symbol"],
                orientation="h",
                name="Top Gainers",
                marker_color=_GAIN_COLOR,
                hovertemplate="%{y}: +%{x:.2f}%<extra></extra>",
            )
        )

    if not losers_df.empty:
        fig.add_trace(
            go.Bar(
                x=losers_df["percentageChange"],
                y=losers_df["symbol"],
                orientation="h",
                name="Top Losers",
                marker_color=_LOSS_COLOR,
                hovertemplate="%{y}: %{x:.2f}%<extra></extra>",
            )
        )

    fig.update_layout(
        title=dict(text="Today's Top Gainers & Losers", font=dict(size=15)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, system-ui, sans-serif", size=13),
        margin=dict(l=10, r=10, t=40, b=10),
        hovermode="y",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        xaxis=dict(title_text="% Change", showgrid=True, gridcolor="rgba(128,128,128,0.15)", zeroline=True),
        yaxis=dict(showgrid=False, autorange="reversed"),
        barmode="overlay",
    )

    logger.info(f"build_gainers_losers_chart: {len(gainers_df)} gainers, {len(losers_df)} losers")
    return fig
