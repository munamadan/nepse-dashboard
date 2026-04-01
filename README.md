# NEPSE Stock Analysis Dashboard

A web-based dashboard for analyzing stocks listed on the Nepal Stock Exchange (NEPSE). Built as a portfolio project to demonstrate data engineering and financial analysis skills.

Live app: https://nepse-dashboard.streamlit.app

---

## What it does

Pick any NEPSE-listed stock and the dashboard shows:

- Current price, day range, and percentage change from the live market feed
- Historical price chart (High, Low, Close) over 30, 60, 90, or 180 days
- Multi-stock comparison — up to 8 stocks normalized to the same starting point so returns are directly comparable
- Sector performance proxy — how the selected stock's sector has moved over the same period, reconstructed from the top 15 most-active member stocks
- Today's top 5 gainers and losers
- Excel export with price history, daily/cumulative returns, and summary statistics

GBIME (Global IME Bank) is the default stock.

---

## How to run locally

```bash
git clone https://github.com/munamadan/nepse-dashboard
cd nepse-dashboard
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Python 3.11 or higher is required.

---

## Known limitations

**Unofficial API.** This dashboard uses [NepseUnofficialApi](https://github.com/basic-bgnr/NepseUnofficialApi), a community-maintained library that reverse-engineers the nepalstock.com API. It has no uptime guarantee and field names may change without notice.

**TLS verification disabled.** NEPSE's server presents an incomplete certificate chain. TLS verification is turned off in the API client. This is acceptable for a read-only portfolio project but would need to be resolved in a production system.

**No open price in historical data.** The historical endpoint does not return an open price. The price chart shows High, Low, and Close only. Open price is available in the live market snapshot for the current trading session.

**Data depth.** The API returns approximately 220 trading days of history. The maximum selectable date range is 180 days.

**Sector proxy, not sector index.** There is no historical sector index endpoint in the API. The sector line is reconstructed by averaging normalized returns from the top 15 most-active stocks in the sector. It is a reasonable proxy but not an official index.

**Cold start delay.** The app is hosted on Streamlit Cloud free tier, which sleeps after inactivity. First load after a period of inactivity can take 20-30 seconds. A loading spinner is shown during this time.

**Snapshot fallback.** If nepalstock.com is unreachable from Streamlit Cloud, the app falls back to a static snapshot captured on 2026-03-28. A banner is shown when this happens.

**Volatility convention.** Annualized volatility uses sqrt(252) trading days, which is the standard convention for equity markets.

---

## Tech stack

- Python 3.11
- Streamlit
- Plotly
- pandas
- NepseUnofficialApi (pinned to commit `2f09fbfdcbaf23545d5755b6f11b367324d5b8a4`)
- openpyxl (Excel export)
