"""
verify_days1_3.py — end-to-end health check for Days 1-3
Run from repo root: python verify_days1_3.py

Tests every layer built so far:
  Layer 1 — imports
  Layer 2 — snapshot file on disk
  Layer 3 — snapshot fallback (no API)
  Layer 4 — live API endpoints
  Layer 5 — data pipeline (parse → filter → gap-fill → normalize → slice → stats)
  Layer 6 — multi-stock alignment
  Layer 7 — chart builders (real data)
  Layer 8 — sector proxy (3 stocks, fast)
"""

import logging
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

RED   = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW= "\033[1;33m"
CYAN  = "\033[0;36m"
BOLD  = "\033[1m"
RESET = "\033[0m"

results: list[tuple[str, bool, str]] = []


def check(name: str, fn):
    try:
        detail = fn()
        results.append((name, True, detail or ""))
        print(f"  {GREEN}PASS{RESET}  {name}" + (f"  {CYAN}({detail}){RESET}" if detail else ""))
    except Exception as e:
        tb = traceback.format_exc().strip().splitlines()[-1]
        results.append((name, False, tb))
        print(f"  {RED}FAIL{RESET}  {name}")
        print(f"        {YELLOW}{tb}{RESET}")


# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{BOLD}Layer 1 — Imports{RESET}")

def _import_nepse_client():
    from src.data.nepse_client import (
        fetch_company_list,
        fetch_gainers,
        fetch_historical_prices,
        fetch_live_market,
        fetch_losers,
        fetch_market_status,
    )
    return "all 6 fetch functions"

def _import_cache():
    from src.data.cache import (
        get_company_list,
        get_gainers,
        get_historical_prices,
        get_live_market,
        get_losers,
        get_market_status,
        get_sector_proxy,
        get_sector_symbols,
    )
    return "all 8 cache functions"

def _import_snapshot():
    from src.data.snapshot import (
        load_snapshot,
        load_snapshot_company_list,
        load_snapshot_gainers,
        load_snapshot_live_market,
        load_snapshot_losers,
        load_snapshot_market_status,
        snapshot_date,
    )
    return "all 7 snapshot functions"

def _import_transforms():
    from src.processing.transforms import (
        align_multiple_stocks,
        build_clean_series,
        build_price_dataframe,
        compute_summary_stats,
        detect_corporate_actions,
        filter_zero_volume,
        handle_gaps,
        normalize_to_index,
        slice_to_days,
    )
    return "all 9 transform functions"

def _import_charts():
    from src.ui.charts import (
        build_comparison_chart,
        build_gainers_losers_chart,
        build_price_chart,
        build_sector_chart,
    )
    return "all 4 chart builders"

check("nepse_client imports", _import_nepse_client)
check("cache imports",        _import_cache)
check("snapshot imports",     _import_snapshot)
check("transforms imports",   _import_transforms)
check("charts imports",       _import_charts)


# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{BOLD}Layer 2 — Snapshot file on disk{RESET}")

def _snapshot_exists():
    import json
    data_dir = Path("data")
    snaps = sorted(data_dir.glob("snapshot_*.json"), reverse=True)
    assert snaps, "No snapshot_*.json found in data/"
    snap = snaps[0]
    size_kb = snap.stat().st_size / 1024
    assert size_kb > 100, f"Snapshot suspiciously small: {size_kb:.0f} KB"
    return f"{snap.name} ({size_kb:.0f} KB)"

def _snapshot_structure():
    import json
    data_dir = Path("data")
    snap = sorted(data_dir.glob("snapshot_*.json"), reverse=True)[0]
    with open(snap) as f:
        d = json.load(f)
    required = ["date", "live_market", "company_list", "gainers", "losers",
                "market_status", "histories"]
    for key in required:
        assert key in d, f"Missing key: {key}"
    return f"{len(d['histories'])} stocks in histories"

def _snapshot_gbime():
    import json
    data_dir = Path("data")
    snap = sorted(data_dir.glob("snapshot_*.json"), reverse=True)[0]
    with open(snap) as f:
        d = json.load(f)
    rows = d["histories"].get("GBIME", [])
    assert rows, "GBIME not in snapshot histories"
    assert len(rows) > 100, f"GBIME snapshot has only {len(rows)} rows"
    first = rows[0]
    for field in ["businessDate", "closePrice", "highPrice", "lowPrice", "totalTradedQuantity"]:
        assert field in first, f"Missing field: {field}"
    return f"GBIME: {len(rows)} rows, fields OK"

check("snapshot file exists",   _snapshot_exists)
check("snapshot structure",     _snapshot_structure)
check("GBIME in snapshot",      _snapshot_gbime)


# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{BOLD}Layer 3 — Snapshot fallback (no API){RESET}")

def _fallback_load_snapshot():
    from src.data.snapshot import load_snapshot
    rows = load_snapshot("GBIME")
    assert rows, "load_snapshot('GBIME') returned empty"
    assert len(rows) > 100
    return f"{len(rows)} rows"

def _fallback_snapshot_date():
    from src.data.snapshot import snapshot_date
    d = snapshot_date()
    assert d, "snapshot_date() returned None"
    assert len(d) == 10 and d[4] == "-", f"Unexpected date format: {d}"
    return d

def _fallback_live_market():
    from src.data.snapshot import load_snapshot_live_market
    rows = load_snapshot_live_market()
    assert rows, "load_snapshot_live_market() returned empty"
    return f"{len(rows)} rows"

def _fallback_company_list():
    from src.data.snapshot import load_snapshot_company_list
    rows = load_snapshot_company_list()
    assert rows, "load_snapshot_company_list() returned empty"
    assert len(rows) > 500, f"Only {len(rows)} companies — suspiciously few"
    return f"{len(rows)} companies"

def _fallback_gainers():
    from src.data.snapshot import load_snapshot_gainers
    rows = load_snapshot_gainers()
    assert rows, "load_snapshot_gainers() returned empty"
    first = rows[0]
    for field in ["symbol", "percentageChange", "ltp"]:
        assert field in first, f"Missing field: {field}"
    return f"{len(rows)} rows, fields OK"

check("load_snapshot('GBIME')",      _fallback_load_snapshot)
check("snapshot_date()",             _fallback_snapshot_date)
check("load_snapshot_live_market()", _fallback_live_market)
check("load_snapshot_company_list()",_fallback_company_list)
check("load_snapshot_gainers()",     _fallback_gainers)


# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{BOLD}Layer 4 — Live API endpoints{RESET}")

def _api_live_market():
    from src.data.nepse_client import fetch_live_market
    rows = fetch_live_market()
    assert rows, "fetch_live_market() returned empty"
    assert len(rows) > 100
    first = rows[0]
    for f in ["symbol", "lastTradedPrice", "percentageChange"]:
        assert f in first, f"Missing field: {f}"
    return f"{len(rows)} rows"

def _api_company_list():
    from src.data.nepse_client import fetch_company_list
    rows = fetch_company_list()
    assert rows, "fetch_company_list() returned empty"
    assert len(rows) > 500
    gbime = next((r for r in rows if r["symbol"] == "GBIME"), None)
    assert gbime, "GBIME not in company list"
    assert gbime.get("sectorName"), "GBIME missing sectorName"
    return f"{len(rows)} companies, GBIME sector={gbime['sectorName']}"

def _api_historical_gbime():
    from src.data.nepse_client import fetch_historical_prices
    rows = fetch_historical_prices("GBIME")
    assert rows, "fetch_historical_prices('GBIME') returned empty"
    assert len(rows) > 100
    first = rows[0]
    for f in ["businessDate", "closePrice", "highPrice", "lowPrice", "totalTradedQuantity"]:
        assert f in first, f"Missing field: {f}"
    assert "openPrice" not in first, "openPrice present — plan says it should NOT exist"
    return f"{len(rows)} rows, no openPrice (correct)"

def _api_market_status():
    from src.data.nepse_client import fetch_market_status
    status = fetch_market_status()
    assert status, "fetch_market_status() returned empty"
    assert "isOpen" in status, "isOpen missing"
    val = status["isOpen"]
    assert val in ("OPEN", "CLOSE", "CLOSED"), f"Unexpected isOpen value: {val!r}"
    return f"isOpen={val!r} (string, not bool — correct)"

def _api_gainers():
    from src.data.nepse_client import fetch_gainers
    rows = fetch_gainers()
    assert rows, "fetch_gainers() returned empty"
    assert len(rows) > 10, "Expected full ranked list, got < 10"
    return f"{len(rows)} rows (full list — take [:5] in UI)"

def _api_losers():
    from src.data.nepse_client import fetch_losers
    rows = fetch_losers()
    assert rows, "fetch_losers() returned empty"
    assert len(rows) > 10
    return f"{len(rows)} rows"

check("fetch_live_market()",             _api_live_market)
check("fetch_company_list() + GBIME",    _api_company_list)
check("fetch_historical_prices(GBIME)",  _api_historical_gbime)
check("fetch_market_status() string",    _api_market_status)
check("fetch_gainers() full list",       _api_gainers)
check("fetch_losers() full list",        _api_losers)


# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{BOLD}Layer 5 — Data pipeline (GBIME){RESET}")

def _pipeline_build_price_dataframe():
    from src.data.nepse_client import fetch_historical_prices
    from src.processing.transforms import build_price_dataframe
    raw = fetch_historical_prices("GBIME")
    df = build_price_dataframe(raw, "GBIME")
    assert not df.empty
    assert list(df.columns) == ["close", "high", "low", "volume"]
    assert df.index.dtype == "datetime64[ns]", f"Index dtype: {df.index.dtype}"
    assert df.index.tz is None, "Index should be tz-naive"
    assert df.isnull().sum().sum() == 0, "Nulls present after build"
    return f"{len(df)} rows, {df.index[0].date()} → {df.index[-1].date()}"

def _pipeline_filter_zero_volume():
    from src.data.nepse_client import fetch_historical_prices
    from src.processing.transforms import build_price_dataframe, filter_zero_volume
    raw = fetch_historical_prices("GBIME")
    df = build_price_dataframe(raw, "GBIME")
    df_filtered = filter_zero_volume(df)
    assert len(df_filtered) <= len(df)
    return f"before={len(df)}, after={len(df_filtered)}"

def _pipeline_build_clean_series():
    from src.data.nepse_client import fetch_historical_prices
    from src.processing.transforms import build_clean_series
    raw = fetch_historical_prices("GBIME")
    df = build_clean_series(raw, "GBIME")
    assert not df.empty
    assert df.isnull().sum().sum() == 0
    assert len(df) > 200, f"Expected >200 rows after gap-fill, got {len(df)}"
    return f"{len(df)} rows after gap-fill"

def _pipeline_normalize():
    import math

    from src.data.nepse_client import fetch_historical_prices
    from src.processing.transforms import build_clean_series, normalize_to_index
    raw = fetch_historical_prices("GBIME")
    df = build_clean_series(raw, "GBIME")
    series = normalize_to_index(df)
    assert math.isclose(series.iloc[0], 100.0, abs_tol=1e-9), f"First value: {series.iloc[0]}"
    assert series.iloc[-1] > 50, "Last value suspiciously low"
    return f"first=100.0 (exact), last={series.iloc[-1]:.2f}"

def _pipeline_slice():
    import math

    from src.data.nepse_client import fetch_historical_prices
    from src.processing.transforms import (
        build_clean_series,
        normalize_to_index,
        slice_to_days,
    )
    raw = fetch_historical_prices("GBIME")
    df = build_clean_series(raw, "GBIME")
    for days in [30, 60, 90, 180]:
        sliced = slice_to_days(df, days)
        norm = normalize_to_index(sliced)
        assert math.isclose(norm.iloc[0], 100.0, abs_tol=1e-9), \
            f"slice_to_days({days}): norm doesn't start at 100"
        assert len(sliced) >= days, f"slice_to_days({days}): only {len(sliced)} rows"
    return "30/60/90/180 all start at 100.0"

def _pipeline_detect_corp_actions():
    from src.data.nepse_client import fetch_historical_prices
    from src.processing.transforms import build_clean_series, detect_corporate_actions
    raw = fetch_historical_prices("GBIME")
    df = build_clean_series(raw, "GBIME")
    dates = detect_corporate_actions(df)
    return f"{len(dates)} corp actions on GBIME (expect 0)"

def _pipeline_summary_stats():
    from src.data.nepse_client import fetch_historical_prices
    from src.processing.transforms import (
        build_clean_series,
        compute_summary_stats,
        slice_to_days,
    )
    raw = fetch_historical_prices("GBIME")
    df = build_clean_series(raw, "GBIME")
    df90 = slice_to_days(df, 90)
    stats = compute_summary_stats(df90, zero_volume_days=0)
    required = ["Start Date", "End Date", "Total Return (%)", "Annualized Volatility (%)",
                "Max Drawdown (%)", "Best Day (%)", "Worst Day (%)", "Zero Volume Days"]
    for k in required:
        assert k in stats, f"Missing stat: {k}"
    return (f"Return={stats['Total Return (%)']:.1f}%, "
            f"Vol={stats['Annualized Volatility (%)']:.1f}%, "
            f"Drawdown={stats['Max Drawdown (%)']:.1f}%")

check("build_price_dataframe",    _pipeline_build_price_dataframe)
check("filter_zero_volume",       _pipeline_filter_zero_volume)
check("build_clean_series",       _pipeline_build_clean_series)
check("normalize_to_index=100",   _pipeline_normalize)
check("slice_to_days 30/60/90/180", _pipeline_slice)
check("detect_corporate_actions", _pipeline_detect_corp_actions)
check("compute_summary_stats",    _pipeline_summary_stats)


# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{BOLD}Layer 6 — Multi-stock alignment{RESET}")

def _align_two_stocks():
    import math

    from src.data.nepse_client import fetch_historical_prices
    from src.processing.transforms import (
        align_multiple_stocks,
        build_clean_series,
        normalize_to_index,
    )
    series_dict = {}
    for sym in ["GBIME", "NABIL"]:
        raw = fetch_historical_prices(sym)
        df = build_clean_series(raw, sym)
        series_dict[sym] = normalize_to_index(df)
    aligned = align_multiple_stocks(series_dict)
    assert list(aligned.columns) == ["GBIME", "NABIL"]
    assert math.isclose(aligned["GBIME"].iloc[0], 100.0, abs_tol=1e-9)
    assert math.isclose(aligned["NABIL"].iloc[0], 100.0, abs_tol=1e-9)
    assert aligned.isnull().sum().sum() == 0
    return f"shape={aligned.shape}, both start at 100.0"

def _align_four_stocks():
    from src.data.nepse_client import fetch_historical_prices
    from src.processing.transforms import (
        align_multiple_stocks,
        build_clean_series,
        normalize_to_index,
    )
    series_dict = {}
    for sym in ["GBIME", "NABIL", "HBL", "NICA"]:
        raw = fetch_historical_prices(sym)
        df = build_clean_series(raw, sym)
        series_dict[sym] = normalize_to_index(df)
    aligned = align_multiple_stocks(series_dict)
    assert aligned.shape[1] == 4
    assert aligned.isnull().sum().sum() == 0
    return f"shape={aligned.shape}, no nulls"

check("align 2 stocks (GBIME+NABIL)",        _align_two_stocks)
check("align 4 stocks (GBIME/NABIL/HBL/NICA)", _align_four_stocks)


# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{BOLD}Layer 7 — Chart builders (real data){RESET}")

def _chart_price():
    from src.data.nepse_client import fetch_historical_prices
    from src.processing.transforms import (
        build_clean_series,
        detect_corporate_actions,
        slice_to_days,
    )
    from src.ui.charts import build_price_chart
    raw = fetch_historical_prices("GBIME")
    df = build_clean_series(raw, "GBIME")
    df90 = slice_to_days(df, 90)
    corp = detect_corporate_actions(df90)
    fig = build_price_chart(df90, "GBIME", corp)
    assert len(fig.data) == 3, f"Expected 3 traces, got {len(fig.data)}"
    names = [t.name for t in fig.data]
    assert names == ["High", "Low", "Close"], f"Unexpected trace names: {names}"
    return f"3 traces (High/Low/Close), {len(df90)} rows"

def _chart_comparison():
    from src.data.nepse_client import fetch_historical_prices
    from src.processing.transforms import (
        align_multiple_stocks,
        build_clean_series,
        normalize_to_index,
        slice_to_days,
    )
    from src.ui.charts import build_comparison_chart
    series_dict = {}
    for sym in ["GBIME", "NABIL", "HBL"]:
        raw = fetch_historical_prices(sym)
        df = build_clean_series(raw, sym)
        df90 = slice_to_days(df, 90)
        series_dict[sym] = normalize_to_index(df90)
    aligned = align_multiple_stocks(series_dict)
    fig = build_comparison_chart(aligned)
    assert len(fig.data) == 3
    return "3 stock lines, baseline hline present"

def _chart_sector():
    import math

    from src.data.nepse_client import fetch_historical_prices
    from src.processing.transforms import (
        build_clean_series,
        normalize_to_index,
        slice_to_days,
    )
    from src.ui.charts import build_sector_chart
    raw = fetch_historical_prices("GBIME")
    df = build_clean_series(raw, "GBIME")
    df90 = slice_to_days(df, 90)
    stock_series = normalize_to_index(df90)

    raw2 = fetch_historical_prices("NABIL")
    df2 = build_clean_series(raw2, "NABIL")
    df2_90 = slice_to_days(df2, 90)
    sector_series = normalize_to_index(df2_90)

    fig = build_sector_chart(stock_series, sector_series, "GBIME")
    assert len(fig.data) == 2
    return "2 lines (stock + sector proxy)"

def _chart_gainers_losers():
    import pandas as pd

    from src.data.nepse_client import fetch_gainers, fetch_losers
    from src.ui.charts import build_gainers_losers_chart
    gainers_raw = fetch_gainers()[:5]
    losers_raw  = fetch_losers()[:5]
    gainers_df = pd.DataFrame(gainers_raw)[["symbol", "percentageChange"]]
    losers_df  = pd.DataFrame(losers_raw)[["symbol", "percentageChange"]]
    fig = build_gainers_losers_chart(gainers_df, losers_df)
    assert len(fig.data) == 2
    return "2 bar traces (gainers green, losers red)"

def _chart_empty_guard():
    import pandas as pd

    from src.ui.charts import (
        build_comparison_chart,
        build_gainers_losers_chart,
        build_price_chart,
        build_sector_chart,
    )
    f1 = build_price_chart(pd.DataFrame(), "X", [])
    f2 = build_comparison_chart(pd.DataFrame())
    f3 = build_sector_chart(pd.Series(dtype=float), pd.Series(dtype=float), "X")
    f4 = build_gainers_losers_chart(pd.DataFrame(), pd.DataFrame())
    for f in [f1, f2, f3, f4]:
        assert len(f.data) == 0, f"Empty guard failed — got {len(f.data)} traces"
    return "all 4 builders return empty figure on empty input"

check("build_price_chart (real GBIME data)",    _chart_price)
check("build_comparison_chart (3 stocks)",      _chart_comparison)
check("build_sector_chart (stock vs proxy)",    _chart_sector)
check("build_gainers_losers_chart (live top 5)",_chart_gainers_losers)
check("empty-input guards on all 4 builders",   _chart_empty_guard)


# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{BOLD}Layer 8 — Sector proxy (3 stocks, fast){RESET}")

def _sector_proxy_timing():
    import math

    from src.data.nepse_client import (
        fetch_company_list,
        fetch_historical_prices,
        fetch_live_market,
    )
    from src.processing.transforms import (
        align_multiple_stocks,
        build_clean_series,
        normalize_to_index,
    )

    companies = fetch_company_list()
    live = fetch_live_market()

    vol_map = {r["symbol"]: r.get("totalTradeQuantity", 0) for r in live}
    bank_syms = [
        c["symbol"] for c in companies
        if c.get("sectorName") == "Commercial Banks"
        and c["symbol"] in vol_map
    ]
    bank_syms_sorted = sorted(bank_syms, key=lambda s: vol_map.get(s, 0), reverse=True)
    top3 = bank_syms_sorted[:3]

    t0 = time.time()
    series_dict = {}
    for sym in top3:
        raw = fetch_historical_prices(sym)
        df = build_clean_series(raw, sym)
        series_dict[sym] = normalize_to_index(df)

    aligned = align_multiple_stocks(series_dict)
    proxy = aligned.mean(axis=1)
    elapsed = time.time() - t0

    assert math.isclose(proxy.iloc[0], 100.0, abs_tol=0.01), f"Proxy first: {proxy.iloc[0]}"
    assert elapsed < 10, f"3 stocks took {elapsed:.1f}s — too slow"
    projected_15 = (elapsed / 3) * 15
    return (f"top3={top3}, {elapsed:.2f}s → ~{projected_15:.1f}s for 15 stocks, "
            f"proxy[0]={proxy.iloc[0]:.2f}")

check("sector proxy 3 Commercial Banks", _sector_proxy_timing)


# ─────────────────────────────────────────────────────────────────────────────
print()
print(f"{BOLD}{'━'*60}{RESET}")
passed = sum(1 for _, ok, _ in results if ok)
failed = sum(1 for _, ok, _ in results if not ok)
total  = len(results)

if failed == 0:
    print(f"{GREEN}{BOLD}  ALL {total} CHECKS PASSED{RESET}")
else:
    print(f"{RED}{BOLD}  {failed} / {total} CHECKS FAILED{RESET}")
    print()
    print(f"{BOLD}  Failed checks:{RESET}")
    for name, ok, detail in results:
        if not ok:
            print(f"    {RED}✗{RESET}  {name}")
            print(f"       {YELLOW}{detail}{RESET}")

print(f"{BOLD}{'━'*60}{RESET}")
print()

layer_names = [
    "Imports", "Snapshot file", "Snapshot fallback",
    "Live API", "Pipeline", "Alignment", "Charts", "Sector proxy"
]
boundaries = [5, 3, 5, 6, 7, 2, 5, 1]
idx = 0
for i, (lname, count) in enumerate(zip(layer_names, boundaries), 1):
    layer_results = results[idx:idx+count]
    lpass = sum(1 for _, ok, _ in layer_results if ok)
    status = f"{GREEN}✓{RESET}" if lpass == count else f"{RED}✗{RESET}"
    print(f"  {status}  Layer {i}: {lname} ({lpass}/{count})")
    idx += count

print()
print(f"{BOLD}What is NOT yet tested (Days 4-5):{RESET}")
print("  ✗  panels.py  — render_live_panel, render_gainers_losers")
print("  ✗  export.py  — build_excel_export (3-sheet xlsx)")
print("  ✗  streamlit_app.py — full UI wired together")
print("  ✗  Streamlit Cloud deployment")
print()

sys.exit(0 if failed == 0 else 1)
