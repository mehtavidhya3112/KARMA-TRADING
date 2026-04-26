# utils/scanner.py
# Exact mirror of KARMA Pine Script signal logic

import math
import warnings
import yfinance as yf
import pandas as pd
import numpy as np
warnings.filterwarnings("ignore")

from utils.indicators import compute_rsi, compute_sma, compute_vwap, is_open_candle_ist

PERIOD_MAP = {
    "1m":"7d","2m":"7d","5m":"60d","15m":"60d","30m":"60d",
    "60m":"730d","1h":"730d","90m":"60d","1d":"5y","1wk":"10y",
}

def _flat(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def _dl(ticker, period, interval, timeout=15):
    try:
        df = yf.download(ticker, period=period, interval=interval,
                         auto_adjust=True, progress=False, timeout=timeout)
        if df is None or len(df) == 0:
            return None
        return _flat(df)
    except Exception:
        return None

def scan_symbol(ticker: str, cfg: dict) -> dict:
    """
    Full Pine Script logic:
    ─────────────────────────────────────────────────
    Structure  : body%, wick%, direction (exact Pine math)
    Volume     : HTF volume vs SMA(volume, v_len)
    PDH/PDL    : daily high[1] / low[1]
    PDH/PDL %  : htf_c >= PDH*(1+pd_pct/100)  [BUY]
                 htf_c <= PDL*(1-pd_pct/100)  [SELL]
    Block      : 9:15 AM IST candle blocked
    Signal     : isNewHTF + bull/bear + all filters
    Live       : RSI(Wilder), VWAP(session), Volume
    History    : last 60 bars of HTF stored
    ─────────────────────────────────────────────────
    """
    R = {
        "ticker":"","signal":"No Signal","htf_dir":"NEUTRAL",
        "body_pct":0.0,"wick_pct":0.0,"vol_ratio":0.0,
        "pdh":float("nan"),"pdl":float("nan"),
        "pdh_dist_pct":0.0,"pdl_dist_pct":0.0,
        "cur_vol":0.0,"cur_vol_ma":0.0,
        "rsi":float("nan"),"vwap":float("nan"),"close":float("nan"),
        "htf_o":float("nan"),"htf_h":float("nan"),
        "htf_l":float("nan"),"htf_c":float("nan"),
        "body_ok":False,"wick_ok":False,"vol_ok":False,
        "pdh_ok":False,"pdl_ok":False,
        "history":[],"error":None,
    }
    R["ticker"] = ticker

    htf    = cfg["htf"]
    v_len  = cfg["v_len"]

    # ── HTF data ─────────────────────────────────────────────
    period = PERIOD_MAP.get(htf, "60d")
    htf_df = _dl(ticker, period, htf)
    if htf_df is None or len(htf_df) < v_len + 2:
        R["error"] = "No HTF data"; return R
    htf_df.dropna(subset=["Open","High","Low","Close","Volume"], inplace=True)
    htf_df["vol_ma"] = compute_sma(htf_df["Volume"], v_len)

    # ── Daily for PDH/PDL (high[1]/low[1]) ───────────────────
    d_df = _dl(ticker, "10d", "1d")
    if d_df is None or len(d_df) < 2:
        R["error"] = "No daily data"; return R
    d_df.dropna(subset=["High","Low"], inplace=True)
    pdH = float(d_df["High"].iloc[-2])
    pdL = float(d_df["Low"].iloc[-2])
    R["pdh"] = pdH
    R["pdl"] = pdL

    # ── Last HTF bar ──────────────────────────────────────────
    last   = htf_df.iloc[-1]
    ts     = htf_df.index[-1]
    htf_o  = float(last["Open"])
    htf_h  = float(last["High"])
    htf_l  = float(last["Low"])
    htf_c  = float(last["Close"])
    htf_v  = float(last["Volume"])
    htf_vma= float(last["vol_ma"]) if not math.isnan(float(last["vol_ma"])) else 0.0

    R.update({"htf_o":htf_o,"htf_h":htf_h,"htf_l":htf_l,"htf_c":htf_c})

    # ── Structure (exact Pine math) ───────────────────────────
    rng     = htf_h - htf_l
    body    = abs(htf_c - htf_o)
    upwick  = htf_h - max(htf_o, htf_c)
    dnwick  = min(htf_o, htf_c) - htf_l
    maxwick = max(upwick, dnwick)
    body_pct = (body / rng * 100.0) if rng > 0 else 0.0
    wick_pct = (maxwick / rng * 100.0) if rng > 0 else 0.0
    is_bull  = htf_c > htf_o
    is_bear  = htf_c < htf_o
    vol_ratio= (htf_v / htf_vma) if htf_vma > 0 else 0.0

    # ── Filters ───────────────────────────────────────────────
    body_ok = (body_pct >= cfg["min_body"] and body_pct <= cfg["max_body"]) if cfg["use_body"] else True
    wick_ok = (wick_pct <= cfg["max_wick"]) if cfg["use_wick"] else True
    vol_ok  = (vol_ratio >= cfg["v_mult"])  if cfg["use_vol"]  else True

    if cfg["use_pd_pct"]:
        pdh_ok = htf_c >= pdH * (1.0 + cfg["pd_pct"] / 100.0)
        pdl_ok = htf_c <= pdL * (1.0 - cfg["pd_pct"] / 100.0)
    else:
        pdh_ok = htf_c > pdH
        pdl_ok = htf_c < pdL

    pdh_dist = ((htf_c - pdH) / pdH * 100.0) if pdH > 0 else 0.0
    pdl_dist = ((pdL - htf_c) / pdL * 100.0) if pdL > 0 else 0.0

    open_candle = is_open_candle_ist(ts)

    # ── Signal ────────────────────────────────────────────────
    pdh_buy  = is_bull and body_ok and wick_ok and vol_ok and pdh_ok and not open_candle
    pdl_sell = is_bear and body_ok and wick_ok and vol_ok and pdl_ok and not open_candle
    signal   = ">>> BUY  PDH <<<" if pdh_buy else ">>> SELL PDL <<<" if pdl_sell else "   No Signal   "

    # ── Live indicators (5m bars) ─────────────────────────────
    ldf = _dl(ticker, "5d", "5m")
    cur_close = htf_c
    cur_vol = cur_vol_ma = float("nan")
    cur_rsi = cur_vwap = float("nan")
    if ldf is not None and len(ldf) > 0:
        ldf.dropna(inplace=True)
        cur_close  = float(ldf["Close"].iloc[-1])
        cur_vol    = float(ldf["Volume"].iloc[-1])
        cur_vol_ma_s = compute_sma(ldf["Volume"], v_len)
        cur_vol_ma = float(cur_vol_ma_s.iloc[-1]) if len(ldf) >= v_len else float("nan")
        if cfg["use_rsi"] and len(ldf) >= cfg["rsi_len"] + 1:
            cur_rsi = float(compute_rsi(ldf["Close"], cfg["rsi_len"]).iloc[-1])
        if cfg["use_vwap"] and len(ldf) > 1:
            cur_vwap = float(compute_vwap(ldf).iloc[-1])

    # ── History: last 60 HTF bars ─────────────────────────────
    history = []
    for i in range(max(0, len(htf_df)-60), len(htf_df)):
        row = htf_df.iloc[i]
        o,h,l,c = float(row["Open"]),float(row["High"]),float(row["Low"]),float(row["Close"])
        r2  = h - l
        b2  = abs(c - o)
        bp2 = (b2/r2*100) if r2 > 0 else 0
        uw2 = h - max(o,c); dw2 = min(o,c) - l
        wp2 = (max(uw2,dw2)/r2*100) if r2 > 0 else 0
        vma2= float(row["vol_ma"]) if not math.isnan(float(row["vol_ma"])) else 0
        vr2 = float(row["Volume"])/vma2 if vma2 > 0 else 0
        b_ok2 = (bp2>=cfg["min_body"] and bp2<=cfg["max_body"]) if cfg["use_body"] else True
        w_ok2 = (wp2<=cfg["max_wick"]) if cfg["use_wick"] else True
        v_ok2 = (vr2>=cfg["v_mult"]) if cfg["use_vol"] else True
        bull2 = c > o; bear2 = c < o
        if cfg["use_pd_pct"]:
            ph_ok2 = c >= pdH*(1+cfg["pd_pct"]/100)
            pl_ok2 = c <= pdL*(1-cfg["pd_pct"]/100)
        else:
            ph_ok2 = c > pdH; pl_ok2 = c < pdL
        buy2  = bull2 and b_ok2 and w_ok2 and v_ok2 and ph_ok2
        sell2 = bear2 and b_ok2 and w_ok2 and v_ok2 and pl_ok2
        sig2  = "BUY" if buy2 else "SELL" if sell2 else "-"
        history.append({
            "time"     : str(htf_df.index[i]),
            "open"     : round(o,2),"high":round(h,2),
            "low"      : round(l,2),"close":round(c,2),
            "body_pct" : round(bp2,1),"wick_pct":round(wp2,1),
            "vol_ratio": round(vr2,2),"signal":sig2,
            "direction": "BULL" if bull2 else "BEAR" if bear2 else "NEUT",
        })

    R.update({
        "signal":signal,"htf_dir":"BULLISH" if is_bull else "BEARISH" if is_bear else "NEUTRAL",
        "body_pct":body_pct,"wick_pct":wick_pct,"vol_ratio":vol_ratio,
        "pdh_dist_pct":pdh_dist,"pdl_dist_pct":pdl_dist,
        "cur_vol":cur_vol,"cur_vol_ma":cur_vol_ma,
        "rsi":cur_rsi,"vwap":cur_vwap,"close":cur_close,
        "body_ok":body_ok,"wick_ok":wick_ok,"vol_ok":vol_ok,
        "pdh_ok":pdh_ok,"pdl_ok":pdl_ok,"history":history,
    })
    return R
