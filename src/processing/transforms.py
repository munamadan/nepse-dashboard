import logging

import pandas as pd

logger = logging.getLogger(__name__)


def build_price_dataframe(raw: list[dict], symbol: str) -> pd.DataFrame:
    if not raw:
        logger.warning(f"build_price_dataframe({symbol}): empty raw input")
        return pd.DataFrame()

    df = pd.DataFrame(raw)

    required = {"businessDate", "closePrice", "highPrice", "lowPrice", "totalTradedQuantity"}
    missing = required - set(df.columns)
    if missing:
        logger.error(f"build_price_dataframe({symbol}): missing fields {missing}")
        return pd.DataFrame()

    df["date"] = pd.to_datetime(df["businessDate"]).dt.tz_localize(None).dt.normalize()
    df = df.set_index("date").sort_index()

    df = df.rename(columns={
        "closePrice": "close",
        "highPrice": "high",
        "lowPrice": "low",
        "totalTradedQuantity": "volume",
    })[["close", "high", "low", "volume"]]

    df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0)

    logger.info(
        f"build_price_dataframe({symbol}): {len(df)} rows, "
        f"{df.index.min().date()} → {df.index.max().date()}"
    )
    return df


def filter_zero_volume(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    mask = df["volume"] > 0
    removed = (~mask).sum()
    if removed > 0:
        logger.warning(
            f"filter_zero_volume: removed {removed} zero-volume rows from {len(df)} total"
        )
    return df[mask]


def find_long_gaps(df: pd.DataFrame, symbol: str, threshold: int = 10) -> None:
    gap_mask = df["close"].isna()
    if not gap_mask.any():
        return
    run_lengths = gap_mask.groupby(
        (gap_mask != gap_mask.shift()).cumsum()
    ).transform("sum")
    long_gap_starts = df.index[gap_mask & (run_lengths > threshold)]
    if len(long_gap_starts) > 0:
        logger.warning(
            f"{symbol}: {len(long_gap_starts)} long gaps (>{threshold} calendar days). "
            f"First few: {long_gap_starts[:3].tolist()}"
        )


def handle_gaps(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    if df.empty:
        return df
    full_range = pd.date_range(df.index.min(), df.index.max(), freq="D")
    df = df.reindex(full_range)
    find_long_gaps(df, symbol)
    filled = df.ffill()
    gap_count = df["close"].isna().sum()
    if gap_count > 0:
        logger.info(f"handle_gaps({symbol}): forward-filled {gap_count} calendar-day gaps")
    return filled


def build_clean_series(raw: list[dict], symbol: str) -> pd.DataFrame:
    df = build_price_dataframe(raw, symbol)
    df = filter_zero_volume(df)
    df = handle_gaps(df, symbol)
    return df


def normalize_to_index(df: pd.DataFrame, column: str = "close") -> pd.Series:
    prices = df[column].dropna()
    if prices.empty:
        logger.warning("normalize_to_index: empty price series")
        return pd.Series(dtype=float)
    if prices.iloc[0] == 0:
        logger.warning("normalize_to_index: first price is zero — cannot normalize")
        return pd.Series(dtype=float)
    return (prices / prices.iloc[0]) * 100


def detect_corporate_actions(
    df: pd.DataFrame, threshold: float = -0.15
) -> pd.Series:
    daily_returns = df["close"].pct_change(fill_method=None)
    suspicious = daily_returns[daily_returns < threshold]
    if not suspicious.empty:
        logger.warning(
            f"Potential corporate actions at: {suspicious.index.tolist()[:5]} "
            f"(returns: {suspicious.round(3).tolist()[:5]})"
        )
    return suspicious


def align_multiple_stocks(series_dict: dict[str, pd.Series]) -> pd.DataFrame:
    if not series_dict:
        return pd.DataFrame()
    df = pd.concat(series_dict, axis=1, join="inner")
    max_len = max(len(s) for s in series_dict.values())
    dropped = max_len - len(df)
    if dropped > 0:
        logger.info(f"align_multiple_stocks: inner join dropped {dropped} dates")
    return df


def slice_to_days(df: pd.DataFrame, days: int) -> pd.DataFrame:
    if df.empty:
        return df
    cutoff = df.index.max() - pd.Timedelta(days=days)
    sliced = df[df.index >= cutoff]
    logger.info(
        f"slice_to_days({days}): {len(sliced)} rows remaining "
        f"({sliced.index.min().date()} → {sliced.index.max().date()})"
    )
    return sliced


def compute_summary_stats(df: pd.DataFrame, zero_volume_days: int = 0) -> dict:
    prices = df["close"].dropna()
    if prices.empty or len(prices) < 2:
        logger.warning("compute_summary_stats: insufficient data")
        return {}

    daily_returns = prices.pct_change(fill_method=None).dropna()
    cum = prices / prices.iloc[0]
    drawdown = (cum - cum.cummax()) / cum.cummax()

    return {
        "Start Date": df.index.min().date(),
        "End Date": df.index.max().date(),
        "Total Return (%)": round((prices.iloc[-1] / prices.iloc[0] - 1) * 100, 2),
        "Annualized Volatility (%)": round(daily_returns.std() * (252**0.5) * 100, 2),
        "Max Drawdown (%)": round(drawdown.min() * 100, 2),
        "Best Day (%)": round(daily_returns.max() * 100, 2),
        "Worst Day (%)": round(daily_returns.min() * 100, 2),
        "Zero Volume Days": zero_volume_days,
    }
