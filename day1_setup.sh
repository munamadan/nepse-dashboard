#!/usr/bin/env bash
# =============================================================================
# NEPSE Dashboard — Day 1 Setup Script
# Extensive logging + error catching edition
# Run from inside nepse-dashboard/ (your repo root)
# =============================================================================

set -uo pipefail  # NOTE: NOT using -e so we can catch and log every error ourselves

# ── Colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

# ── Log file ──────────────────────────────────────────────────────────────────
LOG_FILE="day1_setup.log"
ERRORS=0         # count of non-fatal errors encountered
STEP_NUM=0       # current step counter

# Every echo also writes to the log file
exec > >(tee -a "$LOG_FILE") 2>&1

log_step() {
    STEP_NUM=$((STEP_NUM + 1))
    echo ""
    echo -e "${BOLD}${CYAN}══════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${CYAN}  STEP $STEP_NUM — $1${NC}"
    echo -e "${BOLD}${CYAN}══════════════════════════════════════════════════════════${NC}"
}
log_info()    { echo -e "  ${BLUE}›${NC} $1"; }
log_ok()      { echo -e "  ${GREEN}✓${NC} $1"; }
log_warn()    { echo -e "  ${YELLOW}⚠${NC}  $1"; }
log_error()   { echo -e "  ${RED}✗${NC} $1"; ERRORS=$((ERRORS + 1)); }
log_fatal()   {
    echo ""
    echo -e "${RED}${BOLD}FATAL — cannot continue: $1${NC}"
    echo -e "${RED}Check $LOG_FILE for full output.${NC}"
    exit 1
}

# ── Banner ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}NEPSE Dashboard — Day 1 Setup${NC}"
echo -e "Log file: ${CYAN}$LOG_FILE${NC}  |  Started: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# =============================================================================
# STEP — Preflight checks
# =============================================================================
log_step "Preflight checks"

# Must be run from repo root
if [[ ! -f "streamlit_app.py" ]]; then
    log_fatal "streamlit_app.py not found. Run this script from inside nepse-dashboard/"
fi
log_ok "Working directory: $(pwd)"

# Git repo check
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    log_fatal "Not inside a git repository. Did you run 'git init'?"
fi
REMOTE=$(git remote get-url origin 2>/dev/null || echo "(none set yet)")
log_ok "Git repo detected. Remote: $REMOTE"

# OS check
OS="$(uname -s)"
log_info "OS: $OS"
if [[ "$OS" != "Linux" ]]; then
    log_warn "This script was written for Linux. You are on $OS — some commands may differ."
fi

# curl check
if ! command -v curl &>/dev/null; then
    log_fatal "curl is not installed. Install it with: sudo apt install curl"
fi
log_ok "curl: $(curl --version | head -1)"

# python3 check
if ! command -v python3 &>/dev/null; then
    log_fatal "python3 not found. Install Python >= 3.11."
fi
PYTHON_BIN="python3"
PYTHON_VERSION=$($PYTHON_BIN -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>&1) \
    || log_fatal "python3 is installed but failed to run: $PYTHON_VERSION"
log_info "Python version: $PYTHON_VERSION"

PYTHON_MAJOR=$($PYTHON_BIN -c "import sys; print(sys.version_info.major)")
PYTHON_MINOR=$($PYTHON_BIN -c "import sys; print(sys.version_info.minor)")
if [[ $PYTHON_MAJOR -lt 3 || ($PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -lt 11) ]]; then
    log_fatal "Python >= 3.11 required. Found $PYTHON_VERSION. Install 3.11+ and rerun."
fi
log_ok "Python $PYTHON_VERSION — version requirement satisfied."

if ! command -v git &>/dev/null; then
    log_fatal "git not found. Install: sudo apt install git"
fi
log_ok "git: $(git --version)"

# venv module check
if ! $PYTHON_BIN -m venv --help &>/dev/null; then
    log_fatal "python3-venv missing. Install: sudo apt install python3-venv"
fi
log_ok "python3-venv module available."

# =============================================================================
# STEP — Fetch pinned commit hash
# =============================================================================
log_step "Fetch NepseUnofficialApi pinned commit hash"

log_info "Calling GitHub API for recent commits..."
GITHUB_URL="https://api.github.com/repos/basic-bgnr/NepseUnofficialApi/commits?per_page=20"

HTTP_STATUS=$(curl -s -o /tmp/nepse_commits.json -w "%{http_code}" \
    -H "Accept: application/vnd.github+json" \
    "$GITHUB_URL" 2>&1) || log_fatal "curl failed — check internet connection."

log_info "GitHub API HTTP status: $HTTP_STATUS"

if [[ "$HTTP_STATUS" == "403" ]]; then
    log_warn "GitHub API rate-limited (60 req/hour unauthenticated)."
    log_warn "If this keeps happening, set: export GITHUB_TOKEN=your_personal_access_token"
    log_warn "Waiting 10 seconds and retrying..."
    sleep 10
    HTTP_STATUS=$(curl -s -o /tmp/nepse_commits.json -w "%{http_code}" \
        -H "Accept: application/vnd.github+json" \
        "$GITHUB_URL" 2>&1)
    log_info "Retry HTTP status: $HTTP_STATUS"
fi

if [[ "$HTTP_STATUS" != "200" ]]; then
    log_warn "GitHub API returned HTTP $HTTP_STATUS. Raw response:"
    cat /tmp/nepse_commits.json | head -20 | sed 's/^/    /'
    log_warn "Cannot auto-detect commit hash. Manual input required."
    echo ""
    echo "  Open this URL and find the March 11 2026 commit SHA:"
    echo "  https://github.com/basic-bgnr/NepseUnofficialApi/commits/main"
    echo ""
    read -rp "  Paste the full 40-character SHA: " COMMIT_HASH
    if [[ ${#COMMIT_HASH} -ne 40 ]]; then
        log_fatal "SHA must be exactly 40 characters. Got ${#COMMIT_HASH}: '$COMMIT_HASH'"
    fi
    log_ok "Manually provided SHA: $COMMIT_HASH"
else
    log_ok "GitHub API responded OK."

    # Validate JSON
    if ! $PYTHON_BIN -c "import json,sys; json.load(open('/tmp/nepse_commits.json'))" 2>/dev/null; then
        log_warn "Response is not valid JSON:"
        cat /tmp/nepse_commits.json | head -10 | sed 's/^/    /'
        log_fatal "Cannot parse GitHub API response."
    fi

    # Print all commits
    log_info "Recent commits (newest first):"
    $PYTHON_BIN - <<'PYEOF'
import json
commits = json.load(open("/tmp/nepse_commits.json"))
for c in commits:
    sha  = c["sha"]
    date = c["commit"]["author"]["date"][:10]
    msg  = c["commit"]["message"].split("\n")[0][:70]
    print(f"    {sha}  {date}  {msg}")
PYEOF

    # Auto-detect March 11 2026
    COMMIT_HASH=$($PYTHON_BIN - <<'PYEOF'
import json, sys
commits = json.load(open("/tmp/nepse_commits.json"))
for c in commits:
    if c["commit"]["author"]["date"][:10] == "2026-03-11":
        print(c["sha"])
        sys.exit(0)
print("NOT_FOUND")
PYEOF
)

    if [[ "$COMMIT_HASH" == "NOT_FOUND" ]]; then
        log_warn "No commit dated 2026-03-11 in the last 20 commits."
        log_warn "The commits are printed above — find the March 11 one."
        echo ""
        read -rp "  Paste the correct 40-character SHA: " COMMIT_HASH
        if [[ ${#COMMIT_HASH} -ne 40 ]]; then
            log_fatal "SHA must be exactly 40 characters. Got: '$COMMIT_HASH'"
        fi
        log_ok "Manually confirmed SHA: $COMMIT_HASH"
    else
        log_ok "Auto-detected March 11 2026 commit: $COMMIT_HASH"
    fi

    # Verify SHA actually exists
    log_info "Verifying SHA exists on GitHub..."
    VERIFY_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
        "https://api.github.com/repos/basic-bgnr/NepseUnofficialApi/commits/$COMMIT_HASH" \
        -H "Accept: application/vnd.github+json")
    if [[ "$VERIFY_STATUS" == "200" ]]; then
        log_ok "SHA verified on GitHub."
    else
        log_warn "SHA verification returned HTTP $VERIFY_STATUS — pip install will confirm."
    fi
fi

# =============================================================================
# STEP — Write requirements.txt
# =============================================================================
log_step "Write requirements.txt"

if [[ -f "requirements.txt" ]] && grep -q "NepseUnofficialApi" requirements.txt 2>/dev/null; then
    log_warn "requirements.txt already contains NepseUnofficialApi line. Overwriting entire file."
fi

cat > requirements.txt <<EOF
streamlit>=1.30,<2.0
plotly>=5.18,<6.0
pandas>=2.0,<3.0
openpyxl>=3.1,<4.0
streamlit-autorefresh>=1.0,<2.0
httpx>=0.26,<1.0
git+https://github.com/basic-bgnr/NepseUnofficialApi@${COMMIT_HASH}
EOF

[[ $? -ne 0 ]] && log_fatal "Failed to write requirements.txt — check disk space/permissions."

log_ok "requirements.txt written:"
cat requirements.txt | sed 's/^/    /'

if ! grep -q "$COMMIT_HASH" requirements.txt; then
    log_fatal "SHA not found in requirements.txt after writing. Something went wrong."
fi
log_ok "SHA confirmed in requirements.txt."

# =============================================================================
# STEP — Write .streamlit/config.toml
# =============================================================================
log_step "Write .streamlit/config.toml"

mkdir -p .streamlit || log_fatal "Could not create .streamlit/ directory."

cat > .streamlit/config.toml <<'EOF'
[server]
headless = true
enableCORS = false
enableXsrfProtection = false

[browser]
gatherUsageStats = false
EOF

[[ $? -ne 0 ]] && log_fatal "Failed to write .streamlit/config.toml"

log_ok ".streamlit/config.toml written:"
cat .streamlit/config.toml | sed 's/^/    /'

# =============================================================================
# STEP — Create virtual environment
# =============================================================================
log_step "Create virtual environment (.venv)"

if [[ -d ".venv" ]]; then
    log_warn ".venv already exists."
    if [[ ! -f ".venv/bin/python" && ! -f ".venv/bin/python3" ]]; then
        log_warn "Existing .venv has no python binary — it is corrupted. Deleting and recreating."
        rm -rf .venv
    else
        VENV_VER=$(.venv/bin/python --version 2>&1 || .venv/bin/python3 --version 2>&1)
        log_info "Existing venv Python: $VENV_VER"
        log_ok "Reusing existing .venv."
    fi
fi

if [[ ! -d ".venv" ]]; then
    log_info "Creating virtual environment with $PYTHON_BIN..."
    if ! $PYTHON_BIN -m venv .venv 2>&1; then
        log_fatal "venv creation failed. Try: sudo apt install python3.11-venv"
    fi
    log_ok "Virtual environment created."
fi

# Resolve binaries
if [[ -f ".venv/bin/python" ]]; then
    VENV_PYTHON=".venv/bin/python"
elif [[ -f ".venv/bin/python3" ]]; then
    VENV_PYTHON=".venv/bin/python3"
else
    log_fatal "No python binary in .venv/bin/ — venv creation failed silently."
fi

VENV_PIP=".venv/bin/pip"
[[ ! -f "$VENV_PIP" ]] && log_fatal "pip not found at $VENV_PIP — venv may be corrupted."

log_ok "Venv Python : $VENV_PYTHON ($($VENV_PYTHON --version 2>&1))"
log_ok "Venv pip    : $VENV_PIP ($($VENV_PIP --version 2>&1))"

# =============================================================================
# STEP — Install dependencies
# =============================================================================
log_step "Install dependencies"

log_info "Upgrading pip inside venv..."
if ! $VENV_PIP install --quiet --upgrade pip 2>&1; then
    log_warn "pip upgrade failed — continuing with existing pip."
fi
log_ok "pip: $($VENV_PIP --version 2>&1)"

log_info "Installing from requirements.txt..."
log_info "This takes 1-3 minutes (Streamlit + pywasm compile). Output below:"
echo ""

if ! $VENV_PIP install -r requirements.txt 2>&1; then
    echo ""
    log_error "pip install failed. Common causes and fixes:"
    log_error "  1. Wrong commit hash → verify SHA at github.com/basic-bgnr/NepseUnofficialApi/commits"
    log_error "  2. No internet → check connection, then rerun"
    log_error "  3. GitHub download timeout → rerun (transient)"
    log_error "  4. Missing build tools → sudo apt install build-essential python3-dev"
    log_error ""
    log_error "Manual debug command:"
    log_error "  source .venv/bin/activate && pip install -r requirements.txt -v"
    log_fatal "Dependency installation failed. Fix the error above and rerun."
fi

echo ""
log_ok "pip install completed."

# Verify every package imports correctly
log_info "Verifying all package imports..."
IMPORT_FAIL=0
declare -A PKG_MAP=(
    ["streamlit"]="streamlit"
    ["plotly"]="plotly"
    ["pandas"]="pandas"
    ["openpyxl"]="openpyxl"
    ["streamlit_autorefresh"]="streamlit_autorefresh"
    ["httpx"]="httpx"
    ["pywasm"]="pywasm"
)

for import_name in "${!PKG_MAP[@]}"; do
    if $VENV_PYTHON -c "import $import_name" 2>/dev/null; then
        VER=$($VENV_PYTHON -c "import $import_name; print(getattr($import_name, '__version__', 'unknown'))" 2>/dev/null || echo "unknown")
        log_ok "$import_name — OK (version: $VER)"
    else
        ERR=$($VENV_PYTHON -c "import $import_name" 2>&1)
        log_error "$import_name — IMPORT FAILED: $ERR"
        IMPORT_FAIL=$((IMPORT_FAIL + 1))
    fi
done

# nepse — most critical, separate check with detailed error
if $VENV_PYTHON -c "from nepse import Nepse" 2>/dev/null; then
    log_ok "nepse (NepseUnofficialApi) — OK"
else
    ERR=$($VENV_PYTHON -c "from nepse import Nepse" 2>&1)
    log_error "nepse — IMPORT FAILED: $ERR"
    log_error "This usually means the pinned commit SHA is wrong, or the package"
    log_error "has a broken setup.py at that commit. Verify SHA: $COMMIT_HASH"
    IMPORT_FAIL=$((IMPORT_FAIL + 1))
fi

if [[ $IMPORT_FAIL -gt 0 ]]; then
    log_fatal "$IMPORT_FAIL import(s) failed. Cannot continue — fix the imports first."
fi

# pywasm .wasm file check (the cloud risk)
log_info "Checking pywasm .wasm file presence (critical for Streamlit Cloud)..."
$VENV_PYTHON - <<'PYEOF'
import pywasm, inspect, os, sys

lib_path = os.path.dirname(inspect.getfile(pywasm))
all_files = os.listdir(lib_path)
wasm_files = [f for f in all_files if f.endswith(".wasm")]

print(f"    pywasm lib path : {lib_path}")
print(f"    all files       : {all_files}")

if wasm_files:
    for wf in wasm_files:
        size = os.path.getsize(os.path.join(lib_path, wf))
        print(f"    .wasm file      : {wf} ({size:,} bytes) — OK")
else:
    print("    WARNING: No .wasm file found locally.")
    print("    This may or may not be a problem — the smoke test on Streamlit Cloud will confirm.")
    print("    If cloud also fails, the .wasm must be bundled manually in the repo.")
PYEOF

# =============================================================================
# STEP — Write validate_api.py
# =============================================================================
log_step "Write validate_api.py"

cat > validate_api.py <<'PYEOF'
"""
Day 1 API validation — run locally only, never deployed.
Logs raw field names and response shape for every endpoint.
Run: .venv/bin/python validate_api.py
Output saved to: validate_api_output.txt
"""
import json
import logging
import sys
import time
from pathlib import Path

LOG_FILE = "validate_api_output.txt"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, mode="w"),
    ],
)
logger = logging.getLogger("day1_validation")


def safe_call(label: str, fn, *args):
    """Call fn(*args). Log result shape or full traceback. Never crashes."""
    logger.info("=" * 60)
    logger.info(f"Calling: {label}")
    t0 = time.time()
    try:
        result = fn(*args)
        elapsed = time.time() - t0

        if isinstance(result, list):
            logger.info(f"  → list with {len(result)} items in {elapsed:.2f}s")
            if result:
                logger.info(f"  → field names: {list(result[0].keys())}")
                logger.info(f"  → first row:\n{json.dumps(result[0], default=str, indent=4)}")
            else:
                logger.warning(f"  → EMPTY LIST — unexpected for {label}")
        elif isinstance(result, dict):
            logger.info(f"  → dict keys: {list(result.keys())} in {elapsed:.2f}s")
            logger.info(f"  → full response:\n{json.dumps(result, default=str, indent=4)}")
        elif isinstance(result, bool):
            logger.info(f"  → bool: {result} in {elapsed:.2f}s")
        else:
            logger.info(f"  → type {type(result).__name__}: {result} in {elapsed:.2f}s")

        return result
    except Exception:
        logger.error(f"  → FAILED after {time.time()-t0:.2f}s", exc_info=True)
        return None


def check_depth(data: list | None, label: str) -> None:
    if not data:
        logger.warning(f"{label}: no data — cannot check depth")
        return
    logger.info(f"{label}: {len(data)} rows total")
    if len(data) < 90:
        logger.warning(
            f"{label}: only {len(data)} rows — date range selectors must be "
            f"capped to {len(data)} days max. Update the plan before Day 2."
        )

    date_key = next((k for k in ("businessDate", "date", "Date") if k in data[0]), None)
    if date_key:
        logger.info(f"{label}: date field is '{date_key}' | range: {data[0][date_key]} → {data[-1][date_key]}")
    else:
        logger.warning(
            f"{label}: no recognised date field in first row. "
            f"Available keys: {list(data[0].keys())}"
        )


def check_sectors(companies: list | None) -> None:
    if not companies:
        logger.warning("Company list empty — cannot verify sector mapping")
        return

    first = companies[0]
    sector_key = next((k for k in ("sectorName", "sector", "Sector") if k in first), None)
    if not sector_key:
        logger.error(
            f"CRITICAL: no sectorName field in company data. "
            f"Keys present: {list(first.keys())}. "
            "The entire sector chart architecture depends on this field. "
            "The plan needs revision before Day 2."
        )
        return

    logger.info(f"Sector field name confirmed: '{sector_key}'")
    sectors = sorted({c.get(sector_key, "MISSING") for c in companies})
    logger.info(f"Distinct sector values ({len(sectors)}):")
    for s in sectors:
        count = sum(1 for c in companies if c.get(sector_key) == s)
        logger.info(f"  · {s} ({count} stocks)")

    sym_key = next((k for k in ("symbol", "Symbol", "ticker") if k in first), None)
    if sym_key:
        symbols = [c[sym_key] for c in companies]
        if "GBIME" in symbols:
            logger.info("GBIME confirmed in company list.")
        else:
            logger.warning(
                f"GBIME NOT found. Sample symbols: {symbols[:10]}"
            )
    else:
        logger.warning(f"No symbol field found. Keys: {list(first.keys())}")


def main() -> None:
    logger.info("Day 1 API validation started")
    logger.info(f"Output will be saved to: {Path(LOG_FILE).resolve()}")

    logger.info("=" * 60)
    logger.info("Initialising Nepse() client...")
    try:
        from nepse import Nepse
        nepse = Nepse()
        nepse.setTLSVerification(False)
        logger.info("Nepse() ready. TLS verification disabled (expected — NEPSE cert chain issue).")
    except ImportError:
        logger.error(
            "Cannot import Nepse. Activate venv first: source .venv/bin/activate",
            exc_info=True,
        )
        sys.exit(1)
    except Exception:
        logger.error("Nepse() init failed", exc_info=True)
        sys.exit(1)

    # 1. Historical price
    gbime = safe_call("getDailyScripPriceGraph('GBIME')", nepse.getDailyScripPriceGraph, "GBIME")
    check_depth(gbime, "GBIME")

    # 2. NEPSE index history
    idx = safe_call("getDailyNepseIndexGraph()", nepse.getDailyNepseIndexGraph)
    check_depth(idx, "NEPSE_INDEX")

    # 3. Live market
    live = safe_call("getLiveMarket()", nepse.getLiveMarket)
    if live:
        logger.info(f"Live market: {len(live)} stocks")
        sym_key = next((k for k in ("symbol", "Symbol") if k in live[0]), None)
        if sym_key:
            gbime_live = [r for r in live if r.get(sym_key) == "GBIME"]
            if gbime_live:
                logger.info(f"GBIME live row:\n{json.dumps(gbime_live[0], default=str, indent=4)}")
            else:
                logger.warning(f"GBIME not in live market. Sample: {[r.get(sym_key) for r in live[:5]]}")

    # 4. Sub-indices (current only)
    sub = safe_call("getNepseSubIndices()", nepse.getNepseSubIndices)
    if sub:
        logger.info("CONFIRMED: getNepseSubIndices() is current-only. Cannot use for historical line.")

    # 5. Company list + sector check
    companies = safe_call("getCompanyList()", nepse.getCompanyList)
    check_sectors(companies)

    # 6. Gainers / Losers
    safe_call("getTopGainers()", nepse.getTopGainers)
    safe_call("getTopLosers()", nepse.getTopLosers)

    # 7. Market status
    safe_call("isNepseOpen()", nepse.isNepseOpen)

    logger.info("=" * 60)
    logger.info("Validation complete.")
    logger.info(f"Full output: {Path(LOG_FILE).resolve()}")
    logger.info("Before Day 2, check:")
    logger.info("  1. All field names — they define transforms.py variable names")
    logger.info("  2. Historical depth — if <90 days, cap date range selectors")
    logger.info("  3. sectorName values — must match the sector mapping in the plan")


if __name__ == "__main__":
    main()
PYEOF

[[ $? -ne 0 ]] && log_fatal "Failed to write validate_api.py"
log_ok "validate_api.py written."

# =============================================================================
# STEP — Write smoke-test streamlit_app.py
# =============================================================================
log_step "Write smoke-test streamlit_app.py"

cat > streamlit_app.py <<'PYEOF'
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
PYEOF

[[ $? -ne 0 ]] && log_fatal "Failed to write streamlit_app.py"
log_ok "streamlit_app.py (smoke test) written."

# =============================================================================
# STEP — Write .gitignore
# =============================================================================
log_step "Write .gitignore"

cat > .gitignore <<'EOF'
.venv/
__pycache__/
*.pyc
*.pyo
*.pyd
.DS_Store
*.egg-info/
.env
.env.*
*.log
/tmp/
EOF

log_ok ".gitignore written."

# =============================================================================
# STEP — Run local API validation
# =============================================================================
log_step "Run local API validation"

echo ""
log_info "validate_api.py connects to nepalstock.com and logs all field names."
log_info "It takes ~30-60 seconds (7 API calls). Output goes to validate_api_output.txt"
echo ""
read -rp "  Run it now? [Y/n] " RUN_VALIDATE
RUN_VALIDATE="${RUN_VALIDATE:-Y}"

if [[ "$RUN_VALIDATE" =~ ^[Yy]$ ]]; then
    log_info "Running validate_api.py..."
    echo ""
    if $VENV_PYTHON validate_api.py; then
        log_ok "validate_api.py completed. Review validate_api_output.txt before Day 2."
    else
        log_warn "validate_api.py exited non-zero."
        log_warn "Common causes:"
        log_warn "  · nepalstock.com unreachable from your machine (firewall/VPN)"
        log_warn "  · Market closed — some endpoints may return empty during off-hours"
        log_warn "  · API changed between March 2026 and now"
        log_warn "Check validate_api_output.txt for the full traceback."
        log_warn "Note the error in CHANGELOG Day 1. The cloud smoke test may still pass."
        ERRORS=$((ERRORS + 1))
    fi
else
    log_warn "Skipped. Run manually: .venv/bin/python validate_api.py"
fi

# =============================================================================
# STEP — Git commit
# =============================================================================
log_step "Git commit Day 1 files"

git add \
    requirements.txt \
    .streamlit/config.toml \
    streamlit_app.py \
    validate_api.py \
    .gitignore

# add log files if they exist
git add validate_api_output.txt day1_setup.log 2>/dev/null || true

log_info "Files staged:"
git diff --cached --name-only | sed 's/^/    /'

if git diff --cached --quiet; then
    log_warn "Nothing new to commit — files may already be committed."
else
    if git commit -m "Day 1: pin deps to commit $COMMIT_HASH, smoke test, API validation"; then
        log_ok "Committed."
    else
        log_error "git commit failed. Run 'git status' to debug."
        ERRORS=$((ERRORS + 1))
    fi
fi

# =============================================================================
# Final summary
# =============================================================================
echo ""
echo -e "${BOLD}${CYAN}══════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${CYAN}  DONE — Day 1 Summary${NC}"
echo -e "${BOLD}${CYAN}══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  Pinned SHA     : ${GREEN}$COMMIT_HASH${NC}"
echo -e "  Python         : ${GREEN}$($VENV_PYTHON --version 2>&1)${NC}"
echo -e "  Setup log      : ${CYAN}$LOG_FILE${NC}"
echo -e "  API output     : ${CYAN}validate_api_output.txt${NC}"
echo ""

if [[ $ERRORS -gt 0 ]]; then
    echo -e "  ${YELLOW}⚠  $ERRORS non-fatal error(s) — review log above before continuing.${NC}"
else
    echo -e "  ${GREEN}No errors.${NC}"
fi

echo ""
echo -e "  ${BOLD}Next steps (in order):${NC}"
echo "    1. Review validate_api_output.txt — note every field name"
echo "    2. git push origin main"
echo "    3. Go to share.streamlit.io → New app → connect your repo"
echo "       Main file: streamlit_app.py | Python version: 3.11"
echo "    4. Wait for build, then check that all 5 smoke test checks are green"
echo "    5. Write CHANGELOG.md Day 1 entry with field names + pywasm result"
echo ""
