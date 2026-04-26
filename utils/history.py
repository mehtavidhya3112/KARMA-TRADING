# utils/history.py
import json, os, math, datetime
import pytz

IST       = pytz.timezone("Asia/Kolkata")
HIST_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "signal_history.json")

def _load():
    if not os.path.exists(HIST_FILE): return []
    try:
        with open(HIST_FILE) as f: return json.load(f)
    except: return []

def _save(recs):
    try:
        with open(HIST_FILE,"w") as f: json.dump(recs, f, indent=2, default=str)
    except: pass

def record_signals(results: list, cfg: dict) -> list:
    """Save new BUY/SELL signals. Returns list of newly added records."""
    recs  = _load()
    now   = datetime.datetime.now(IST)
    today = now.strftime("%Y-%m-%d")
    seen  = {(r["ticker"], r["signal"]) for r in recs if r.get("date") == today}
    new   = []
    for r in results:
        sig = r.get("signal","")
        if "BUY" not in sig and "SELL" not in sig: continue
        if r.get("error"): continue
        key = (r["ticker"], sig.strip())
        if key in seen: continue
        is_bull  = r["htf_dir"] == "BULLISH"
        rel_dist = r["pdh_dist_pct"] if is_bull else r["pdl_dist_pct"]
        rec = {
            "date":today, "time":now.strftime("%H:%M:%S"),
            "datetime":now.strftime("%Y-%m-%d %H:%M:%S IST"),
            "ticker":r["ticker"], "signal":sig.strip(),
            "direction":r["htf_dir"],
            "close":   round(r["close"],2)    if not math.isnan(r.get("close",float("nan")))   else None,
            "pdh":     round(r["pdh"],2)      if not math.isnan(r.get("pdh",float("nan")))     else None,
            "pdl":     round(r["pdl"],2)      if not math.isnan(r.get("pdl",float("nan")))     else None,
            "pdh_dist":round(rel_dist,2),
            "body_pct":round(r["body_pct"],1),
            "wick_pct":round(r["wick_pct"],1),
            "vol_ratio":round(r["vol_ratio"],2),
            "rsi":     round(r["rsi"],1)      if not math.isnan(r.get("rsi",float("nan")))     else None,
            "vwap":    round(r["vwap"],2)     if not math.isnan(r.get("vwap",float("nan")))    else None,
            "htf":cfg.get("htf",""),
        }
        recs.append(rec); seen.add(key); new.append(rec)
    _save(recs)
    return new

def get_all():
    return list(reversed(_load()))

def get_today():
    today = datetime.datetime.now(IST).strftime("%Y-%m-%d")
    return list(reversed([r for r in _load() if r.get("date")==today]))

def get_by_ticker(ticker):
    return list(reversed([r for r in _load() if r.get("ticker")==ticker]))

def clear_all():
    if os.path.exists(HIST_FILE): os.remove(HIST_FILE)

def stats():
    recs = _load()
    if not recs: return {"total":0,"buy":0,"sell":0,"days":0,"tickers":0}
    return {
        "total":len(recs),
        "buy":  sum(1 for r in recs if "BUY"  in r.get("signal","")),
        "sell": sum(1 for r in recs if "SELL" in r.get("signal","")),
        "days": len(set(r.get("date","") for r in recs)),
        "tickers": len(set(r.get("ticker","") for r in recs)),
    }
