## Day 1 — 2026-03-26

### Built
- Repo structure created, all placeholder files committed
- requirements.txt written with pinned SHA: `2f09fbfdcbaf23545d5755b6f11b367324d5b8a4` (March 11 2026 merge commit)
- `.streamlit/config.toml` written
- Python 3.11.9 venv created, all dependencies installed and import-verified
- `validate_api.py` written and executed successfully against live nepalstock.com
- `streamlit_app.py` smoke test written (pending cloud deployment)
- Repo pushed to: https://github.com/munamadan/nepse-dashboard

### Broke
- `getDailyNepseIndexGraph()` returned a `list[list]` (nested lists), not `list[dict]`.
  `validate_api.py` crashed on `result[0].keys()` with `AttributeError: 'list' object has no attribute 'keys'`.
  The raw structure of the index response is unknown — must be inspected on Day 2.

### Fixed
- Nothing yet — both issues below are open going into Day 2.

### Decisions Made
- Pinned to merge commit `2f09fbfdcbaf` (March 11 2026) not the bug-fix commit directly,
  as the merge commit is the canonical published state of that release.
- pywasm `.wasm` file is NOT present in the locally installed package
  (`['__init__.py', 'core.py', 'leb128.py', 'log.py', 'opcode.py', '__pycache__']` — no `.wasm`).
  pywasm 1.2.2 appears to embed the wasm binary differently than expected (possibly compiled into
  Python, or loaded from a different path). Smoke test on Streamlit Cloud will determine if this
  is actually a problem. Noted as risk — do not assume resolved.

### Critical Findings — Must Resolve Before Writing Any Processing Code

**Finding 1 — WRONG ENDPOINT: `getDailyScripPriceGraph` returns intraday data, not historical daily OHLCV.**

The API hit `POST /api/nots/market/graphdata/daily/341` and returned only 26 rows with fields:
  `contractQuantity` (nullable), `contractRate` (price), `time` (Unix timestamp, e.g. 1774501260)

This is today's intraday price graph — 26 price points across today's trading session.
It is NOT a historical daily close series. The field name `contractRate` is not `close`,
there is no open/high/low/volume, and 26 rows is one trading day's worth of ticks, not 26 days.

The entire historical price chart and comparison chart depend on finding the correct
historical daily OHLCV endpoint. This must be resolved as the first task on Day 2
before any other code is written.

**Finding 2 — `getDailyNepseIndexGraph` returns `list[list]`, not `list[dict]`.**

66 items returned but each item is itself a list (not a dict with named fields).
The structure is unknown. Must be inspected raw on Day 2.
The NEPSE index overlay on all charts depends on this endpoint being parseable.

### Confirmed Field Names (for endpoints that worked correctly)

getLiveMarket():
  securityId, securityName, symbol, indexId, openPrice, highPrice, lowPrice,
  totalTradeQuantity, totalTradeValue, lastTradedPrice, percentageChange,
  lastUpdatedDateTime, lastTradedVolume, previousClose, averageTradedPrice

getNepseSubIndices():
  id, index, change, perChange, currentValue
  Confirmed current-only. 13 sectors match plan exactly.

getCompanyList():
  id, companyName, symbol, securityName, status, companyEmail, website,
  sectorName, regulatoryBody, instrumentType
  622 companies. sectorName confirmed. GBIME confirmed (securityId: 341).
  All 13 sector names match the plan's sector mapping exactly.

getTopGainers() / getTopLosers():
  symbol, ltp, cp, pointChange, percentageChange, securityName, securityId
  Returns 91 and 176 items respectively (not top-10 — full ranked list, take [:5]).

isNepseOpen():
  Returns dict: {isOpen: "OPEN"/"CLOSED", asOf: datetime string, id: int}
  Note: isOpen is a string "OPEN"/"CLOSED", NOT a boolean. Plan assumed boolean.

### Open Questions
1. What is the actual historical daily OHLCV endpoint in NepseUnofficialApi?
   Is there a `getStockHistory()`, `getScripOHLC()`, or similar method?
2. What is the raw structure of `getDailyNepseIndexGraph()` list items?
3. Does pywasm 1.2.2 actually need a .wasm file, or is the wasm bytecode
   compiled into the Python module? (Cloud smoke test will answer this.)

### Next Session
Day 2 first task: Open the NepseUnofficialApi source at the pinned commit and list
every available method on the Nepse class. Find the correct historical OHLCV endpoint.
Do not write any processing code until the correct endpoint is confirmed and its
field names are logged.


## Day 1 — 2026-03-26

### Built
- Repo structure created, all placeholder files committed
- requirements.txt written with pinned SHA: `2f09fbfdcbaf23545d5755b6f11b367324d5b8a4` (March 11 2026 merge commit)
- `.streamlit/config.toml` written
- Python 3.11.9 venv created, all dependencies installed and import-verified
- `validate_api.py` written and executed successfully against live nepalstock.com
- `streamlit_app.py` smoke test written (pending cloud deployment)
- Repo pushed to: https://github.com/munamadan/nepse-dashboard

### Broke
- `getDailyNepseIndexGraph()` returned a `list[list]` (nested lists), not `list[dict]`.
  `validate_api.py` crashed on `result[0].keys()` with `AttributeError: 'list' object has no attribute 'keys'`.
  The raw structure of the index response is unknown — must be inspected on Day 2.

### Fixed
- Nothing yet — both issues below are open going into Day 2.

### Decisions Made
- Pinned to merge commit `2f09fbfdcbaf` (March 11 2026) not the bug-fix commit directly,
  as the merge commit is the canonical published state of that release.
- pywasm `.wasm` file is NOT present in the locally installed package
  (`['__init__.py', 'core.py', 'leb128.py', 'log.py', 'opcode.py', '__pycache__']` — no `.wasm`).
  pywasm 1.2.2 appears to embed the wasm binary differently than expected (possibly compiled into
  Python, or loaded from a different path). Smoke test on Streamlit Cloud will determine if this
  is actually a problem. Noted as risk — do not assume resolved.

### Critical Findings — Must Resolve Before Writing Any Processing Code

**Finding 1 — WRONG ENDPOINT: `getDailyScripPriceGraph` returns intraday data, not historical daily OHLCV.**

The API hit `POST /api/nots/market/graphdata/daily/341` and returned only 26 rows with fields:
  `contractQuantity` (nullable), `contractRate` (price), `time` (Unix timestamp, e.g. 1774501260)

This is today's intraday price graph — 26 price points across today's trading session.
It is NOT a historical daily close series. The field name `contractRate` is not `close`,
there is no open/high/low/volume, and 26 rows is one trading day's worth of ticks, not 26 days.

The entire historical price chart and comparison chart depend on finding the correct
historical daily OHLCV endpoint. This must be resolved as the first task on Day 2
before any other code is written.

**Finding 2 — `getDailyNepseIndexGraph` returns `list[list]`, not `list[dict]`.**

66 items returned but each item is itself a list (not a dict with named fields).
The structure is unknown. Must be inspected raw on Day 2.
The NEPSE index overlay on all charts depends on this endpoint being parseable.

### Confirmed Field Names (for endpoints that worked correctly)

getLiveMarket():
  securityId, securityName, symbol, indexId, openPrice, highPrice, lowPrice,
  totalTradeQuantity, totalTradeValue, lastTradedPrice, percentageChange,
  lastUpdatedDateTime, lastTradedVolume, previousClose, averageTradedPrice

getNepseSubIndices():
  id, index, change, perChange, currentValue
  Confirmed current-only. 13 sectors match plan exactly.

getCompanyList():
  id, companyName, symbol, securityName, status, companyEmail, website,
  sectorName, regulatoryBody, instrumentType
  622 companies. sectorName confirmed. GBIME confirmed (securityId: 341).
  All 13 sector names match the plan's sector mapping exactly.

getTopGainers() / getTopLosers():
  symbol, ltp, cp, pointChange, percentageChange, securityName, securityId
  Returns 91 and 176 items respectively (not top-10 — full ranked list, take [:5]).

isNepseOpen():
  Returns dict: {isOpen: "OPEN"/"CLOSED", asOf: datetime string, id: int}
  Note: isOpen is a string "OPEN"/"CLOSED", NOT a boolean. Plan assumed boolean.

### Open Questions
1. What is the actual historical daily OHLCV endpoint in NepseUnofficialApi?
   Is there a `getStockHistory()`, `getScripOHLC()`, or similar method?
2. What is the raw structure of `getDailyNepseIndexGraph()` list items?
3. Does pywasm 1.2.2 actually need a .wasm file, or is the wasm bytecode
   compiled into the Python module? (Cloud smoke test will answer this.)

### Next Session
Day 2 first task: Open the NepseUnofficialApi source at the pinned commit and list
every available method on the Nepse class. Find the correct historical OHLCV endpoint.
Do not write any processing code until the correct endpoint is confirmed and its
field names are logged.

## Day 2 — 2026-03-27

### Built
- src/data/nepse_client.py — all raw API calls with threading.Lock singleton,
  standard logging pattern on every fetch function
- src/data/cache.py — st.cache_data wrappers with TTLs, get_sector_proxy()
  orchestration with top-N-by-volume stock selection
- src/data/snapshot.py — stub returning [] with warning log (Day 3 implementation)
- src/processing/transforms.py — full pipeline: build_price_dataframe,
  filter_zero_volume, handle_gaps, build_clean_series, normalize_to_index,
  detect_corporate_actions, align_multiple_stocks, slice_to_days,
  compute_summary_stats
- test_pipeline.py — end-to-end validation script, all 7 checks passed

### Decisions Made
- Sector chart: PRIMARY implementation confirmed (5 stocks = 0.2s,
  15 stocks ≈ 1s). Sector reconstruction is fast enough — peer-picker
  fallback not needed.
- Date range selector options: 30 / 60 / 90 / 180 days max.
  365-day option removed — API only returns ~220 trading days (~365 calendar days).
- No openPrice in historical data. Price chart uses High/Low/Close only.
  Open is available in getLiveMarket() for the live panel only.

### Confirmed Pipeline Behavior
- GBIME: 220 trading rows → 365 calendar rows after gap-fill (145 gaps ffilled)
- normalize_to_index: confirmed starts at exactly 100.0
- align_multiple_stocks: GBIME + NABIL both start at 100.0 after inner join
- KDBY: 2 zero-volume rows filtered, 12 long gaps detected — logging works
- detect_corporate_actions: 0 events on GBIME over past year

### Open Questions
- None blocking Day 3

### Next Session
Day 3 first task: write scripts/capture_snapshot.py, run it to capture live
data, commit the JSON, then implement src/ui/charts.py with all four
Plotly figure builders.

## Day 3 — 2026-03-28

### Built
- scripts/capture_snapshot.py — top 30 by volume + always-include list,
  writes data/snapshot_YYYY-MM-DD.json (2.2MB, 33 stocks)
- src/data/snapshot.py — full implementation: load_snapshot, loaders for all
  endpoints, snapshot_date(); picks newest JSON automatically
- src/data/nepse_client.py — snapshot fallback on all 5 fetch functions
- src/ui/charts.py — build_price_chart, build_comparison_chart,
  build_sector_chart, build_gainers_losers_chart
- test_charts.py — 6 tests, all passing
- verify_days1_3.py — 34 checks across 8 layers, all 34 passing

### Fixed
- add_vline crash: Plotly requires pd.Timestamp(date_str).timestamp() * 1000
  on datetime axes, not a plain date string

### Confirmed Numbers (live data, 2026-03-28)
- GBIME: 219 trading rows, 362 calendar rows after gap-fill
- GBIME 90-day: Return=11.8%, Vol=19.9%, Drawdown=-5.1%
- Sector proxy (3 Commercial Banks): 0.08s → ~0.4s projected for 15 stocks
- isOpen returns 'CLOSE' (not 'CLOSED') — check must handle both spellings

### Decisions Made
- isOpen value observed as 'CLOSE' not 'CLOSED' — update market status check
  in panels.py to: data.get("isOpen") in ("OPEN",) as the open check,
  anything else is closed

### Next Session
Day 4: write src/ui/panels.py (render_live_panel, render_gainers_losers),
write src/ui/export.py (build_excel_export), build minimal app shell,
deploy to Streamlit Cloud.
