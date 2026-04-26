# utils/indicators.py
# Exact replicas of Pine Script ta.* functions

import math
import numpy as np
import pandas as pd
import pytz

IST = pytz.timezone("Asia/Kolkata")


def compute_rsi(series: pd.Series, length: int = 14) -> pd.Series:
    """Wilder RSI — identical to Pine ta.rsi()"""
    delta = series.diff()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)
    avg_g = gain.ewm(alpha=1/length, min_periods=length, adjust=False).mean()
    avg_l = loss.ewm(alpha=1/length, min_periods=length, adjust=False).mean()
    rs    = avg_g / avg_l.replace(0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


def compute_sma(series: pd.Series, length: int) -> pd.Series:
    """Simple Moving Average — Pine ta.sma()"""
    return series.rolling(window=length, min_periods=length).mean()


def compute_vwap(df: pd.DataFrame) -> pd.Series:
    """Session VWAP with daily reset — Pine ta.vwap(hlc3)"""
    hlc3 = (df["High"] + df["Low"] + df["Close"]) / 3.0
    tpv  = hlc3 * df["Volume"]

    if df.index.tzinfo is not None:
        dates = df.index.tz_convert(IST).normalize()
    else:
        dates = df.index.normalize()

    vals, cum_tpv, cum_vol, prev = [], 0.0, 0.0, None
    for i in range(len(df)):
        d = dates[i]
        if d != prev:
            cum_tpv = cum_vol = 0.0
            prev = d
        cum_tpv += float(tpv.iloc[i])
        cum_vol  += float(df["Volume"].iloc[i])
        vals.append(cum_tpv / cum_vol if cum_vol > 0 else float("nan"))
    return pd.Series(vals, index=df.index)


def is_open_candle_ist(ts) -> bool:
    """True if bar == 09:15 IST — blocks first candle signals"""
    try:
        if hasattr(ts, "tzinfo") and ts.tzinfo is not None:
            t = ts.astimezone(IST)
        else:
            t = IST.localize(ts.to_pydatetime())
        return t.hour == 9 and t.minute == 15
    except Exception:
        return False
