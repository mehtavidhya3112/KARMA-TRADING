# utils/bg_scanner.py
# Runs scan in a daemon thread — continues across page switches

import threading, datetime, math
import pytz
from utils.scanner import scan_symbol

IST   = pytz.timezone("Asia/Kolkata")
_lock = threading.Lock()
_state = {
    "running":False,"done":False,"progress":0.0,
    "current":"","scanned":0,"total":0,
    "results":[],"scan_time":None,"cfg":{},
    "stop_flag":False,"new_signals":[],
}
_thread = None

def _run(cfg, stocks):
    total, results = len(stocks), []
    with _lock:
        _state.update({"running":True,"done":False,"progress":0.0,
                       "scanned":0,"total":total,"results":[],
                       "scan_time":None,"stop_flag":False,
                       "new_signals":[],"cfg":cfg.copy()})
    for i, ticker in enumerate(stocks):
        with _lock:
            if _state["stop_flag"]: break
            _state["current"] = ticker
            _state["scanned"] = i
        try:
            r = scan_symbol(ticker, cfg)
        except Exception as e:
            r = {"ticker":ticker,"signal":"No Signal","htf_dir":"NEUTRAL",
                 "body_pct":0.0,"wick_pct":0.0,"vol_ratio":0.0,
                 "pdh":float("nan"),"pdl":float("nan"),
                 "pdh_dist_pct":0.0,"pdl_dist_pct":0.0,
                 "cur_vol":0.0,"cur_vol_ma":0.0,
                 "rsi":float("nan"),"vwap":float("nan"),"close":float("nan"),
                 "htf_o":float("nan"),"htf_h":float("nan"),
                 "htf_l":float("nan"),"htf_c":float("nan"),
                 "body_ok":False,"wick_ok":False,"vol_ok":False,
                 "pdh_ok":False,"pdl_ok":False,"history":[],"error":str(e)}
        results.append(r)
        with _lock:
            _state["progress"] = (i+1)/total
            _state["scanned"]  = i+1

    results.sort(key=lambda r: 0 if "BUY" in r.get("signal","")
                               else 1 if "SELL" in r.get("signal","")
                               else 3 if r.get("error") else 2)
    new_sigs = []
    try:
        from utils.history import record_signals
        new_sigs = record_signals(results, cfg)
    except: pass

    try:
        from utils.stock_history import save_scan_snapshot
        save_scan_snapshot(results, cfg)
    except: pass

    # Save full snapshot of all 206 stocks for history page
    try:
        from utils.stock_history import save_scan_snapshot
        save_scan_snapshot(results, cfg)
    except: pass

    with _lock:
        _state.update({"results":results,"running":False,"done":True,
                       "progress":1.0,"current":"",
                       "scan_time":datetime.datetime.now(IST),
                       "new_signals":new_sigs})

class BgScanner:
    @staticmethod
    def start(cfg, stocks):
        global _thread
        with _lock: _state["stop_flag"] = True
        if _thread and _thread.is_alive(): _thread.join(timeout=2)
        _thread = threading.Thread(target=_run, args=(cfg,stocks), daemon=True)
        _thread.start()

    @staticmethod
    def stop():
        with _lock: _state["stop_flag"] = True

    @staticmethod
    def state():
        with _lock: return dict(_state)

    @staticmethod
    def is_running():
        with _lock: return _state["running"]

    @staticmethod
    def results():
        with _lock: return list(_state["results"])

    @staticmethod
    def pop_new_signals():
        with _lock:
            ns = list(_state["new_signals"])
            _state["new_signals"] = []
            return ns
