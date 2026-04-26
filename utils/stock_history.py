# utils/stock_history.py
"""
Stock Status History
────────────────────
On every completed scan, saves the FULL status of all 206 stocks
(not just signals — every stock's body%, wick%, vol ratio, direction,
PDH, PDL, signal status, RSI, VWAP, close price) with timestamp.

This gives a complete picture of where every stock stood at each scan.

Storage: stock_history.json  (one record per stock per scan)
"""

import json, os, math, datetime
import pytz

IST       = pytz.timezone("Asia/Kolkata")
HIST_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "stock_history.json")

def _load():
    if not os.path.exists(HIST_FILE): return []
    try:
        with open(HIST_FILE) as f: return json.load(f)
    except: return []

def _save(recs):
    try:
        with open(HIST_FILE, "w") as f: json.dump(recs, f, indent=2, default=str)
    except: pass

def _safe(val, decimals=2):
    """Round float safely, return None if nan."""
    try:
        if math.isnan(float(val)): return None
        return round(float(val), decimals)
    except: return None


def save_scan_snapshot(results: list, cfg: dict):
    """
    Called after every completed scan.
    Saves one record per stock into stock_history.json.
    Each record contains ALL filter values and the final signal status.
    """
    recs = _load()
    now  = datetime.datetime.now(IST)
    scan_id   = now.strftime("%Y%m%d_%H%M%S")
    scan_date = now.strftime("%Y-%m-%d")
    scan_time = now.strftime("%H:%M:%S")
    scan_ts   = now.strftime("%Y-%m-%d %H:%M:%S IST")

    for r in results:
        if r.get("error"): continue   # skip errored stocks
        ticker  = r.get("ticker","")
        sig     = r.get("signal","").strip()
        is_bull = r.get("htf_dir","") == "BULLISH"
        rel_dist= r.get("pdh_dist_pct",0) if is_bull else r.get("pdl_dist_pct",0)

        recs.append({
            # ── Scan metadata ─────────────────────────────────
            "scan_id"  : scan_id,
            "date"     : scan_date,
            "time"     : scan_time,
            "datetime" : scan_ts,
            "htf"      : cfg.get("htf",""),

            # ── Stock ─────────────────────────────────────────
            "ticker"   : ticker,

            # ── Signal status ─────────────────────────────────
            "signal"   : sig,
            "direction": r.get("htf_dir","NEUTRAL"),

            # ── Price ─────────────────────────────────────────
            "close"    : _safe(r.get("close")),
            "pdh"      : _safe(r.get("pdh")),
            "pdl"      : _safe(r.get("pdl")),

            # ── HTF candle values ─────────────────────────────
            "htf_open" : _safe(r.get("htf_o")),
            "htf_high" : _safe(r.get("htf_h")),
            "htf_low"  : _safe(r.get("htf_l")),
            "htf_close": _safe(r.get("htf_c")),

            # ── Filter values ─────────────────────────────────
            "body_pct" : _safe(r.get("body_pct"), 1),
            "wick_pct" : _safe(r.get("wick_pct"), 1),
            "vol_ratio": _safe(r.get("vol_ratio"), 2),
            "dist_pct" : _safe(rel_dist, 2),

            # ── Filter pass/fail ──────────────────────────────
            "body_ok"  : bool(r.get("body_ok", False)),
            "wick_ok"  : bool(r.get("wick_ok", False)),
            "vol_ok"   : bool(r.get("vol_ok",  False)),
            "pdh_ok"   : bool(r.get("pdh_ok",  False)),
            "pdl_ok"   : bool(r.get("pdl_ok",  False)),

            # ── Live indicators ───────────────────────────────
            "rsi"      : _safe(r.get("rsi"), 1),
            "vwap"     : _safe(r.get("vwap"), 2),
        })

    _save(recs)


def get_latest_snapshot():
    """
    Returns the most recent scan snapshot — one record per stock.
    (i.e., all records whose scan_id == the latest scan_id)
    """
    recs = _load()
    if not recs: return []
    latest_id = recs[-1]["scan_id"]
    return [r for r in recs if r.get("scan_id") == latest_id]


def get_all_snapshots():
    """Returns all historical records newest-first."""
    return list(reversed(_load()))


def get_snapshots_for_ticker(ticker: str):
    """Returns all scan records for a specific ticker, newest-first."""
    recs = _load()
    return list(reversed([r for r in recs if r.get("ticker") == ticker]))


def get_scan_ids():
    """Returns list of unique scan_ids (newest first) with date/time."""
    recs  = _load()
    seen  = {}
    for r in recs:
        sid = r.get("scan_id","")
        if sid not in seen:
            seen[sid] = {"scan_id": sid, "datetime": r.get("datetime",""),
                         "date": r.get("date",""), "time": r.get("time",""),
                         "htf": r.get("htf","")}
    return list(reversed(list(seen.values())))


def clear_all():
    if os.path.exists(HIST_FILE): os.remove(HIST_FILE)


def summary_stats():
    recs = _load()
    if not recs: return {"total_records":0,"unique_scans":0,"unique_tickers":0,
                         "total_buy":0,"total_sell":0}
    return {
        "total_records" : len(recs),
        "unique_scans"  : len(set(r.get("scan_id","") for r in recs)),
        "unique_tickers": len(set(r.get("ticker","") for r in recs)),
        "total_buy"     : sum(1 for r in recs if "BUY"  in r.get("signal","")),
        "total_sell"    : sum(1 for r in recs if "SELL" in r.get("signal","")),
    }
