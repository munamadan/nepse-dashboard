import io
import logging

import pandas as pd

from src.processing.transforms import compute_summary_stats

logger = logging.getLogger(__name__)


def build_excel_export(df: pd.DataFrame, symbol: str, date_range_days: int) -> bytes:
    try:
        zero_vol_days = int((df["volume"] == 0).sum()) if "volume" in df.columns else 0
        summary = compute_summary_stats(df, zero_vol_days)

        sheet1 = df[["high", "low", "close", "volume"]].copy()
        sheet1.index.name = "Date"
        sheet1.columns = ["High", "Low", "Close", "Volume"]

        close = df["close"].copy()
        daily_ret = close.pct_change(fill_method=None) * 100
        cum_ret = (close / close.iloc[0] - 1) * 100

        sheet2 = pd.DataFrame(
            {
                "Daily Return (%)": daily_ret.round(4),
                "Cumulative Return (%)": cum_ret.round(4),
            }
        )
        sheet2.index.name = "Date"

        sheet3_rows = [
            ("Symbol", symbol),
            ("Date Range (days)", date_range_days),
            ("Start Date", str(summary.get("start_date", ""))),
            ("End Date", str(summary.get("end_date", ""))),
            ("Total Return (%)", summary.get("total_return_pct", "")),
            ("Annualized Volatility (%)", summary.get("annualized_vol_pct", "")),
            ("Max Drawdown (%)", summary.get("max_drawdown_pct", "")),
            ("Best Day (%)", summary.get("best_day_pct", "")),
            ("Worst Day (%)", summary.get("worst_day_pct", "")),
            ("Zero Volume Days", summary.get("zero_volume_days", zero_vol_days)),
        ]
        sheet3 = pd.DataFrame(sheet3_rows, columns=["Metric", "Value"])

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            sheet1.to_excel(writer, sheet_name="Price History")
            sheet2.to_excel(writer, sheet_name="Returns")
            sheet3.to_excel(writer, sheet_name="Summary Stats", index=False)

        buffer.seek(0)
        data = buffer.read()
        logger.info("build_excel_export(%s, %dd): %d bytes", symbol, date_range_days, len(data))
        return data

    except Exception:
        logger.error("build_excel_export(%s) failed", symbol, exc_info=True)
        return b""
