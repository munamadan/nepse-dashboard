"""
Day 1 smoke test — validates pywasm + API on Streamlit Cloud.
Replace this file with the real app on Day 5.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import os
import inspect
import traceback
import streamlit as st

st.set_page_config(page_title="NEPSE — Day 1 Smoke Test", page_icon="📈")
st.title("📈 NEPSE Dashboard — Day 1 Smoke Test")
st.caption("Temporary validation page. All checks must be green before Day 2.")

# ── 1. pywasm ────────────────────────────────────────────────────────────────
st.subheader("1. pywasm import + .wasm file")
try:
    import pywasm
    lib_path = os.path.dirname(inspect.getfile(pywasm))
    all_files = os.listdir(lib_path)
    wasm_files = [f for f in all_files if f.endswith(".wasm")]

    st.success("✓ pywasm imported successfully")
    st.code(f"Library path: {lib_path}\nAll files: {all_files}")

    if wasm_files:
        for wf in wasm_files:
            size = os.path.getsize(os.path.join(lib_path, wf))
            st.success(f"✓ .wasm file found: {wf} ({size:,} bytes)")
    else:
        st.error(
            "✗ No .wasm file in pywasm directory.\n\n"
            "pywasm cannot load its WebAssembly binary — every API call will fail.\n"
            "This must be resolved before Day 2. Check the library's GitHub issues.\n\n"
            f"Files present: {all_files}\nPath: {lib_path}"
        )
        st.stop()
except ImportError as e:
    st.error(f"✗ pywasm import failed:\n\n{e}\n\n{traceback.format_exc()}")
    st.stop()
except Exception as e:
    st.error(f"✗ Unexpected pywasm error:\n\n{e}\n\n{traceback.format_exc()}")
    st.stop()

# ── 2. nepse import ──────────────────────────────────────────────────────────
st.subheader("2. NepseUnofficialApi import")
try:
    from nepse import Nepse
    st.success("✓ from nepse import Nepse — OK")
except ImportError as e:
    st.error(
        f"✗ Cannot import Nepse:\n\n{e}\n\n"
        "Check requirements.txt has the correct pinned commit hash.\n\n"
        f"{traceback.format_exc()}"
    )
    st.stop()

# ── 3. Client init ───────────────────────────────────────────────────────────
st.subheader("3. Nepse() client init (loads WebAssembly)")
try:
    with st.spinner("Initialising Nepse client — loads .wasm binary, takes ~5 seconds..."):
        nepse = Nepse()
        nepse.setTLSVerification(False)
    st.success("✓ Nepse() initialised. TLS verification disabled (expected for NEPSE).")
except Exception as e:
    st.error(
        f"✗ Nepse() init failed:\n\n{e}\n\n"
        "Possible causes:\n"
        "· .wasm file not at expected relative path inside the installed package\n"
        "· pywasm version incompatible with this commit of NepseUnofficialApi\n"
        "· Network error during WebAssembly init\n\n"
        f"{traceback.format_exc()}"
    )
    st.stop()

# ── 4. getCompanyList ────────────────────────────────────────────────────────
st.subheader("4. getCompanyList() — confirms API reachability")
try:
    with st.spinner("Calling getCompanyList()..."):
        companies = nepse.getCompanyList()
    if not companies:
        st.error(
            "✗ getCompanyList() returned an empty list.\n\n"
            "Possible causes:\n"
            "· nepalstock.com is blocking Streamlit Cloud shared IPs\n"
            "· The API response structure changed\n"
            "· TLS error that setTLSVerification(False) didn't catch"
        )
        st.stop()
    st.success(f"✓ {len(companies)} companies returned")
    st.json(companies[0])
    sectors = sorted({c.get("sectorName", "MISSING") for c in companies})
    if "MISSING" in sectors:
        st.warning(f"⚠ Some companies missing sectorName. Sectors found: {sectors}")
    else:
        st.info(f"Sector names ({len(sectors)}): {sectors}")
except Exception as e:
    st.error(
        f"✗ getCompanyList() failed:\n\n{e}\n\n"
        "If this is a connection error, nepalstock.com may be blocking this IP.\n"
        "The static snapshot fallback (Day 3) handles this case.\n\n"
        f"{traceback.format_exc()}"
    )
    st.stop()

# ── 5. GBIME historical depth ────────────────────────────────────────────────
st.subheader("5. getDailyScripPriceGraph('GBIME') — historical depth")
try:
    with st.spinner("Fetching GBIME price history..."):
        gbime = nepse.getDailyScripPriceGraph("GBIME")
    if not gbime:
        st.error("✗ getDailyScripPriceGraph('GBIME') returned empty.")
        st.stop()
    st.success(f"✓ {len(gbime)} rows of historical data")
    if len(gbime) < 90:
        st.warning(
            f"⚠ Only {len(gbime)} days available. "
            "Date range selectors must be capped. Note in CHANGELOG Day 1."
        )
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Oldest row (field names):**", gbime[0])
    with col2:
        st.write("**Most recent row:**", gbime[-1])
except Exception as e:
    st.error(f"✗ GBIME fetch failed:\n\n{e}\n\n{traceback.format_exc()}")

st.divider()
st.success(
    "✅ All checks passed.\n\n"
    "Record the field names shown above in CHANGELOG.md Day 1 entry. "
    "These become the source of truth for transforms.py on Day 2."
)
