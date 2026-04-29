"""
KARMA PA Breakout Scanner — Streamlit Web Dashboard v4
Compatible with Streamlit Cloud (Python 3.12)
"""

import streamlit as st

# ── MUST be first Streamlit call ─────────────────────────────
st.set_page_config(
    page_title="KARMA PA Scanner",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)

import pandas as pd
import yfinance as yf
import datetime
import warnings
warnings.filterwarnings("ignore")

# RSI calculation — pure pandas, no extra library needed
def _calc_rsi(series, window=14):
    delta  = series.diff()
    gain   = delta.clip(lower=0)
    loss   = -delta.clip(upper=0)
    avg_g  = gain.ewm(com=window - 1, min_periods=window).mean()
    avg_l  = loss.ewm(com=window - 1, min_periods=window).mean()
    rs     = avg_g / avg_l.replace(0, float("nan"))
    return 100 - (100 / (1 + rs))

# ── CSS ──────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Inter:wght@300;400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background: #0D0D0D;
    color: #E0E0E0;
}

.karma-header {
    background: linear-gradient(135deg,#0F3460 0%,#16213E 50%,#0D0D0D 100%);
    border: 1px solid #00E5FF33;
    border-radius: 12px;
    padding: 28px 32px;
    margin-bottom: 20px;
}
.karma-title {
    font-family: 'Space Mono', monospace;
    font-size: 2rem;
    font-weight: 700;
    color: #00E5FF;
    margin: 0;
}
.karma-sub {
    font-size: .85rem;
    color: #666688;
    margin-top: 6px;
    font-family: 'Space Mono', monospace;
}

.alert-card {
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 10px;
    border-left: 4px solid;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
}
.alert-card.buy  { background: #0a1f0a; border-color: #00E676; }
.alert-card.sell { background: #1f0a0a; border-color: #FF1744; }
.alert-sym   { font-family: 'Space Mono', monospace; font-size: 1rem; font-weight: 700; }
.alert-badge { font-size: .75rem; font-weight: 700; padding: 3px 10px;
               border-radius: 20px; font-family: 'Space Mono', monospace; }
.badge-buy   { background: #00E67222; color: #00E676; border: 1px solid #00E676; }
.badge-sell  { background: #FF174422; color: #FF1744; border: 1px solid #FF1744; }
.alert-meta  { font-size: .8rem; color: #888; }
.alert-price { font-family: 'Space Mono', monospace; font-size: .95rem; }

.notif-buy  { background: #002200; border: 2px solid #00E676; border-radius: 10px;
              padding: 16px 20px; margin: 6px 0; }
.notif-sell { background: #220000; border: 2px solid #FF1744; border-radius: 10px;
              padding: 16px 20px; margin: 6px 0; }
.notif-title { font-family: 'Space Mono', monospace; font-size: 1.1rem;
               font-weight: 700; margin-bottom: 6px; }
.notif-body  { font-size: .85rem; color: #CCCCCC;
               font-family: 'Space Mono', monospace; line-height: 1.6; }

.section-hdr { font-family: 'Space Mono', monospace; font-size: .8rem;
               color: #00E5FF; text-transform: uppercase; letter-spacing: 2px;
               border-bottom: 1px solid #333355; padding-bottom: 6px; margin: 18px 0 12px; }
.no-signal   { text-align: center; padding: 50px; color: #444466;
               font-family: 'Space Mono', monospace; font-size: .9rem; }

section[data-testid="stSidebar"] {
    background: #0F0F1A;
    border-right: 1px solid #1A1A2E;
}
</style>
""", unsafe_allow_html=True)

# ── Watchlist ─────────────────────────────────────────────────
WATCHLIST = [
    "MAZDOCK.NS","ICICIBANK.NS","HDFCBANK.NS","RELIANCE.NS","SBIN.NS",
    "BHARTIARTL.NS","AXISBANK.NS","BEL.NS","HAL.NS","INFY.NS",
    "ETERNAL.NS","TCS.NS","VEDL.NS","LT.NS","ONGC.NS",
    "SHRIRAMFIN.NS","BSE.NS","HINDALCO.NS","UNITDSPR.NS","INDIGO.NS",
    "KOTAKBANK.NS","M&M.NS","BDL.NS","ITC.NS","SUNPHARMA.NS",
    "BAJFINANCE.NS","NATIONALUM.NS","SOLARINDS.NS","PERSISTENT.NS","RVNL.NS",
    "NTPC.NS","TATASTEEL.NS","MARUTI.NS","ADANIGREEN.NS","POWERGRID.NS",
    "DIXON.NS","COALINDIA.NS","MCX.NS","ASHOKLEY.NS","IDEA.NS",
    "CUMMINSIND.NS","BAJAJFINSV.NS","GRASIM.NS","OIL.NS","ADANIPORTS.NS",
    "BAJAJ-AUTO.NS","BPCL.NS","HINDUNILVR.NS","GODREJPROP.NS","IRFC.NS",
    "ULTRACEMCO.NS","IOC.NS","ADANIENT.NS","CANBK.NS","PFC.NS",
    "KAYNES.NS","POLICYBZR.NS","MAXHEALTH.NS","BHARATFORG.NS","PETRONET.NS",
    "LUPIN.NS","DLF.NS","TIINDIA.NS","JIOFIN.NS","HINDPETRO.NS",
    "POWERINDIA.NS","EICHERMOT.NS","BHEL.NS","BANKBARODA.NS","NMDC.NS",
    "HCLTECH.NS","SUZLON.NS","TITAN.NS","POLYCAB.NS","TMPV.NS",
    "HEROMOTOCO.NS","UNIONBANK.NS","INDHOTEL.NS","GAIL.NS","ABB.NS",
    "WAAREEENER.NS","ASIANPAINT.NS","TVSMOTOR.NS","ANGELONE.NS","CGPOWER.NS",
    "BRITANNIA.NS","MFSL.NS","VBL.NS","KPITTECH.NS","COFORGE.NS",
    "HDFCLIFE.NS","JSWENERGY.NS","SWIGGY.NS","UPL.NS","RECLTD.NS",
    "MARICO.NS","SAIL.NS","BLUESTARCO.NS","ASTRAL.NS","MUTHOOTFIN.NS",
    "TORNTPHARM.NS","WIPRO.NS","GMRAIRPORT.NS","APOLLOHOSP.NS","HDFCAMC.NS",
    "PNB.NS","DIVISLAB.NS","HINDZINC.NS","CHOLAFIN.NS","SBILIFE.NS",
    "KEI.NS","ABCAPITAL.NS","IDFCFIRSTB.NS","NAUKRI.NS","BANDHANBNK.NS",
    "ADANIENSOL.NS","APLAPOLLO.NS","IREDA.NS","LODHA.NS","TATAPOWER.NS",
    "JSWSTEEL.NS","TECHM.NS","CDSL.NS","TRENT.NS","PAYTM.NS",
    "AMBER.NS","MOTHERSON.NS","SIEMENS.NS","DRREDDY.NS","YESBANK.NS",
    "BANKINDIA.NS","FORTIS.NS","TATAELXSI.NS","AUBANK.NS","FEDERALBNK.NS",
    "INDUSINDBK.NS","NHPC.NS","CAMS.NS","NESTLEIND.NS","TATACONSUM.NS",
    "VOLTAS.NS","INDIANB.NS","BIOCON.NS","GODREJCP.NS","AUROPHARMA.NS",
    "LTM.NS","SRF.NS","INDUSTOWER.NS","JINDALSTEL.NS","MANAPPURAM.NS",
    "CIPLA.NS","GLENMARK.NS","KALYANKJIL.NS","DMART.NS","JUBLFOOD.NS",
    "LAURUSLABS.NS","PGEL.NS","PIDILITIND.NS","NBCC.NS","PAGEIND.NS",
    "NYKAA.NS","MANKIND.NS","INOXWIND.NS","SUPREMEIND.NS","LTF.NS",
    "SBICARD.NS","SAMMAANCAP.NS","ICICIGI.NS","RBLBANK.NS","HAVELLS.NS",
    "MPHASIS.NS","OBEROIRLTY.NS","AMBUJACEM.NS","OFSS.NS","LICI.NS",
    "BOSCHLTD.NS","PREMIERENE.NS","DABUR.NS","ICICIPRULI.NS","IEX.NS",
    "PRESTIGE.NS","LICHSGFIN.NS","HUDCO.NS","COLPAL.NS","SHREECEM.NS",
    "UNOMINDA.NS","CONCOR.NS","PHOENIXLTD.NS","PNBHOUSING.NS","PATANJALI.NS",
    "ZYDUSLIFE.NS","KFINTECH.NS","TORNTPOWER.NS","DALBHARAT.NS","PIIND.NS",
    "TATATECH.NS","BAJAJHLDNG.NS","SONACOMS.NS","360ONE.NS","DELHIVERY.NS",
    "NUVAMA.NS","EXIDEIND.NS","CROMPTON.NS","ALKEM.NS","SYNGENE.NS",
    "PPLPHARMA.NS",
]

# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⬡ KARMA PA  v4")
    st.caption(f"📋 {len(WATCHLIST)} stocks")
    st.markdown("---")

    st.markdown("**📊 Timeframes**")
    TF = ["1m","2m","5m","15m","30m","60m","1h","4h","1d"]
    htf      = st.selectbox("HTF Timeframe",   TF, index=TF.index("1h"))
    chart_tf = st.selectbox("Chart Timeframe", TF, index=TF.index("15m"))
    st.markdown("---")

    use_body = st.checkbox("🕯 Enable Body % Filter", value=True)
    if use_body:
        min_body = st.slider("Min Body %", 50.0, 95.0, 75.0, 0.5)
        max_body = st.slider("Max Body %", 55.0, 99.0, 80.0, 0.5)
    else:
        min_body = max_body = 0.0
        st.caption("Body % filter disabled")
    st.markdown("---")

    use_wick = st.checkbox("🕯 Enable Wick % Filter", value=True)
    if use_wick:
        max_wick = st.slider("Max Wick %", 1.0, 49.0, 20.0, 0.5)
    else:
        max_wick = 100.0
        st.caption("Wick % filter disabled")
    st.markdown("---")

    use_vol = st.checkbox("📈 Enable Volume Filter", value=True)
    if use_vol:
        vol_len  = st.slider("Vol MA Length",     5,   100, 20)
        vol_mult = st.slider("Volume >= X × Avg", 1.0, 5.0, 1.5, 0.1)
    else:
        vol_len = 20; vol_mult = 1.0
        st.caption("Volume filter disabled")
    st.markdown("---")

    use_pd_pct = st.checkbox("📉 Enable PDH/PDL % Filter", value=True)
    if use_pd_pct:
        pd_pct = st.slider("Min % above PDH / below PDL", 0.1, 10.0, 1.0, 0.1)
    else:
        pd_pct = 0.0
        st.caption("PDH/PDL % filter disabled")
    st.markdown("---")

    st.markdown("**⚙ Indicators**")
    use_rsi  = st.checkbox("Enable RSI",  value=True)
    rsi_len  = st.slider("RSI Length", 2, 50, 14) if use_rsi else 14
    use_vwap = st.checkbox("Enable VWAP", value=True)
    st.markdown("---")

    st.markdown("**🔔 Alerts**")
    al_pdh_buy  = st.checkbox("PDH Breakout BUY Alert",  value=True)
    al_pdl_sell = st.checkbox("PDL Breakdown SELL Alert", value=True)
    st.markdown("---")

    st.markdown("**🔔 Notifications**")
    show_notif_panel = st.checkbox("Show Notification Panel", value=True)

cfg = dict(
    HTF=htf, CHART_TF=chart_tf,
    USE_BODY=use_body, MIN_BODY=min_body, MAX_BODY=max_body,
    USE_WICK=use_wick, MAX_WICK=max_wick,
    USE_VOL=use_vol,   VOL_LEN=vol_len,  VOL_MULT=vol_mult,
    USE_PD_PCT=use_pd_pct, PD_PCT=pd_pct,
    USE_RSI=use_rsi, RSI_LEN=rsi_len, USE_VWAP=use_vwap,
)


# ── Scanner functions ─────────────────────────────────────────

def _nc(df):
    df.columns = [
        c[0].lower() if isinstance(c, tuple) else c.lower()
        for c in df.columns
    ]
    return df

def _ist(df):
    df.index = pd.to_datetime(df.index)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df.index = df.index.tz_convert("Asia/Kolkata")
    return df

def fetch(sym, interval, period):
    df = yf.download(sym, interval=interval, period=period,
                     auto_adjust=True, progress=False)
    if df.empty:
        return df
    return _ist(_nc(df))

def calc_htf(htf_df, cfg):
    o, h, l, c, v = (htf_df[k] for k in ["open","high","low","close","volume"])
    rng = h - l
    body = (c - o).abs()
    uw = h - pd.concat([o, c], axis=1).max(axis=1)
    dw = pd.concat([o, c], axis=1).min(axis=1) - l
    mw = pd.concat([uw, dw], axis=1).max(axis=1)
    htf_df["body_pct"]  = (body / rng * 100).where(rng > 0, 0.0)
    htf_df["wick_pct"]  = (mw   / rng * 100).where(rng > 0, 0.0)
    vma = v.rolling(cfg["VOL_LEN"]).mean()
    htf_df["vol_ma"]    = vma
    htf_df["vol_ratio"] = (v / vma).where(vma > 0, 0.0)
    htf_df["is_bull"]   = c > o
    htf_df["is_bear"]   = c < o
    if cfg["USE_BODY"]:
        htf_df["body_ok"] = (
            (htf_df["body_pct"] >= cfg["MIN_BODY"]) &
            (htf_df["body_pct"] <= cfg["MAX_BODY"])
        )
    else:
        htf_df["body_ok"] = True
    htf_df["wick_ok"] = (htf_df["wick_pct"] <= cfg["MAX_WICK"]) if cfg["USE_WICK"] else True
    htf_df["vol_ok"]  = (htf_df["vol_ratio"] >= cfg["VOL_MULT"]) if cfg["USE_VOL"]  else True
    return htf_df

def attach_pdh_pdl(ltf, daily):
    daily = daily.copy()
    daily["pdh"] = daily["high"].shift(1)
    daily["pdl"] = daily["low"].shift(1)
    ltf = ltf.copy()
    ltf["_d"] = ltf.index.normalize()
    ltf = ltf.merge(daily[["pdh","pdl"]], left_on="_d", right_index=True, how="left")
    ltf.drop(columns=["_d"], inplace=True)
    return ltf

def pdh_pdl_ok(htf_c, pdH, pdL, cfg):
    if cfg["USE_PD_PCT"]:
        return (htf_c >= pdH * (1 + cfg["PD_PCT"] / 100),
                htf_c <= pdL * (1 - cfg["PD_PCT"] / 100))
    return htf_c > pdH, htf_c < pdL

def calc_indicators(ltf, cfg):
    if cfg["USE_RSI"]:
        ltf["rsi"] = _calc_rsi(ltf["close"], window=cfg["RSI_LEN"])
    else:
        ltf["rsi"] = float("nan")

    if cfg["USE_VWAP"]:
        hlc3 = (ltf["high"] + ltf["low"] + ltf["close"]) / 3
        ltf["_d"] = ltf.index.date
        parts = []
        for _, g in ltf.groupby("_d"):
            parts.append(
                (hlc3.loc[g.index] * g["volume"]).cumsum() / g["volume"].cumsum()
            )
        ltf["vwap"] = pd.concat(parts).sort_index()
        ltf.drop(columns=["_d"], inplace=True)
    else:
        ltf["vwap"] = float("nan")

    ltf["vol_ma_ltf"] = ltf["volume"].rolling(cfg["VOL_LEN"]).mean()
    return ltf

def gen_signals(htf_df, ltf_df, cfg):
    cols = ["open","high","low","close","volume","vol_ma",
            "body_pct","wick_pct","vol_ratio","is_bull","is_bear",
            "body_ok","wick_ok","vol_ok"]
    hr = htf_df[cols].copy()
    hr.columns = ["h_" + c for c in cols]

    def align(ts):
        p = htf_df.index[htf_df.index <= ts]
        return p[-1] if len(p) else None

    ltf_df = ltf_df.copy()
    ltf_df["htf_key"]    = [align(t) for t in ltf_df.index]
    ltf_df["is_new_htf"] = ltf_df["htf_key"] != ltf_df["htf_key"].shift(1)
    for col in hr.columns:
        ltf_df[col] = ltf_df["htf_key"].map(hr[col])

    ltf_df["pdh_buy"]  = False
    ltf_df["pdl_sell"] = False
    dph = dpl = False

    for i, row in ltf_df.iterrows():
        if row["is_new_htf"]:
            dph = dpl = False
        oc = (i.hour == 9 and i.minute == 15)
        hc = row.get("h_close", float("nan"))
        pH = row.get("pdh",     float("nan"))
        pL = row.get("pdl",     float("nan"))
        if pd.isna(hc) or pd.isna(pH) or pd.isna(pL):
            continue
        pho, plo = pdh_pdl_ok(hc, pH, pL, cfg)
        if (row["is_new_htf"] and row.get("h_is_bull") and row.get("h_body_ok")
                and row.get("h_wick_ok") and row.get("h_vol_ok")
                and pho and not dph and not oc):
            ltf_df.at[i, "pdh_buy"] = True
            dph = True
        if (row["is_new_htf"] and row.get("h_is_bear") and row.get("h_body_ok")
                and row.get("h_wick_ok") and row.get("h_vol_ok")
                and plo and not dpl and not oc):
            ltf_df.at[i, "pdl_sell"] = True
            dpl = True
    return ltf_df

def scan_one(sym, cfg):
    try:
        htf   = fetch(sym, cfg["HTF"],      "90d").dropna()
        ltf   = fetch(sym, cfg["CHART_TF"], "30d").dropna()
        daily = fetch(sym, "1d",             "60d").dropna()
        if htf.empty or ltf.empty or daily.empty:
            return None
        daily.index = daily.index.normalize()
        htf = calc_htf(htf, cfg)
        ltf = attach_pdh_pdl(ltf, daily)
        ltf = calc_indicators(ltf, cfg)
        ltf = gen_signals(htf, ltf, cfg)

        lh = htf.iloc[-1]
        ll = ltf.iloc[-1]
        hc = float(lh["close"])
        pH = float(ll.get("pdh", float("nan")))
        pL = float(ll.get("pdl", float("nan")))

        pdh_dist = ((hc - pH) / pH * 100) if pH > 0 else 0.0
        pdl_dist = ((pL - hc) / pL * 100) if pL > 0 else 0.0
        ib  = bool(lh["is_bull"])
        ie  = bool(lh["is_bear"])
        rel = pdh_dist if ib else (pdl_dist if ie else 0.0)
        pok = (rel >= cfg["PD_PCT"]) if cfg["USE_PD_PCT"] else True

        pdh_b = bool(ll.get("pdh_buy",  False))
        pdl_s = bool(ll.get("pdl_sell", False))
        cr    = float(ll.get("rsi",  float("nan")))
        cv    = float(ll.get("vwap", float("nan")))
        cc    = float(ll["close"])
        vm    = float(ll.get("vol_ma_ltf", float("nan")))
        vol   = float(ll["volume"])

        s_pdpct = (f"{round(rel*10)/10:.1f}%  (min {cfg['PD_PCT']:.1f}%)"
                   if cfg["USE_PD_PCT"] else "disabled")
        s_rsi   = (f"{round(cr*10)/10:.1f}"
                   if cfg["USE_RSI"] and not pd.isna(cr) else "disabled")
        if cfg["USE_VWAP"] and not pd.isna(cv):
            s_vwap = f"{cv:.2f}  ({'above' if cc >= cv else 'below'})"
        else:
            s_vwap = "disabled"
        s_cvol = (f"{round(vol/1000*10)/10:.1f}K  ({round(vol/vm*100):.0f}% avg)"
                  if not pd.isna(vm) and vm > 0 else "N/A")

        return dict(
            sym=sym.replace(".NS", ""), ticker=sym,
            pdh_buy=pdh_b, pdl_sell=pdl_s,
            close=cc, pdH=pH, pdL=pL,
            s_pdh=f"{pH:.2f}", s_pdl=f"{pL:.2f}",
            s_pdpct=s_pdpct, s_rsi=s_rsi, s_vwap=s_vwap,
            s_cvol=s_cvol, cur_rsi=cr,
            body_pct=float(lh["body_pct"]),
            wick_pct=float(lh["wick_pct"]),
            vol_ratio=float(lh["vol_ratio"]),
            s_dir="BULLISH" if ib else ("BEARISH" if ie else "NEUTRAL"),
            pdpct_ok=pok,
        )
    except Exception:
        return None


# ── Main Layout ───────────────────────────────────────────────
st.markdown("""
<div class="karma-header">
  <div class="karma-title">⬡ KARMA Price Action Scanner  v4</div>
  <div class="karma-sub">
    PDH / PDL Breakout Dashboard — 200 NSE Stocks  |  All filters individually enable/disable
  </div>
</div>
""", unsafe_allow_html=True)

run_btn = st.button("▶  RUN SCAN — All 200 Stocks",
                    use_container_width=True, type="primary")

if run_btn:
    start      = datetime.datetime.now()
    all_alerts = []
    notif_html = []

    pb     = st.progress(0)
    status = st.empty()
    feed   = st.empty()
    live   = []

    for i, sym in enumerate(WATCHLIST):
        pb.progress((i + 1) / len(WATCHLIST))
        status.markdown(f"`Scanning [{i+1}/{len(WATCHLIST)}]  {sym}`")
        d = scan_one(sym, cfg)

        if d and (d["pdh_buy"] or d["pdl_sell"]):
            all_alerts.append(d)
            tag = "🟢 BUY" if d["pdh_buy"] else "🔴 SELL"
            lvl_key = "s_pdh" if d["pdh_buy"] else "s_pdl"
            live.append(
                f"`{tag}`  **{d['sym']}**  ₹{d['close']:.2f}  "
                f"{'PDH' if d['pdh_buy'] else 'PDL'}: {d[lvl_key]}"
            )

            if show_notif_panel:
                cls   = "notif-buy" if d["pdh_buy"] else "notif-sell"
                icon  = "🟢" if d["pdh_buy"] else "🔴"
                stype = "PDH BREAKOUT — BUY" if d["pdh_buy"] else "PDL BREAKDOWN — SELL"
                lvl   = d["s_pdh"] if d["pdh_buy"] else d["s_pdl"]
                lbl   = "PDH" if d["pdh_buy"] else "PDL"
                now_s = datetime.datetime.now().strftime("%H:%M:%S")
                notif_html.append(f"""
                <div class="{cls}">
                  <div class="notif-title">{icon}  {stype}  —  {d['sym']}</div>
                  <div class="notif-body">
                    Close : ₹{d['close']:.2f} &nbsp;|&nbsp;
                    {lbl}: {lvl} &nbsp;|&nbsp;
                    PDH/PDL%: {d['s_pdpct']}<br>
                    RSI : {d['s_rsi']} &nbsp;|&nbsp;
                    VWAP : {d['s_vwap']} &nbsp;|&nbsp;
                    Time : {now_s}
                  </div>
                </div>""")

        if live:
            feed.markdown("\n\n".join(live[-8:]))

    elapsed = (datetime.datetime.now() - start).total_seconds()
    pb.empty()
    status.empty()
    feed.empty()

    buys  = [d for d in all_alerts if d["pdh_buy"]]
    sells = [d for d in all_alerts if d["pdl_sell"]]

    # Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🔍 Scanned",      len(WATCHLIST))
    c2.metric("🟢 BUY Signals",  len(buys))
    c3.metric("🔴 SELL Signals", len(sells))
    c4.metric("⏱ Time",         f"{elapsed:.0f}s")
    st.caption(
        f"Last scan: {datetime.datetime.now().strftime('%d %b %Y  %H:%M:%S')}"
        f"  |  HTF: {htf}  |  Chart: {chart_tf}"
    )

    # Notification Panel
    if show_notif_panel and notif_html:
        st.markdown("---")
        st.markdown('<div class="section-hdr">🔔 Client Notifications</div>',
                    unsafe_allow_html=True)
        st.markdown("\n".join(notif_html), unsafe_allow_html=True)

    st.markdown("---")

    # BUY Alerts
    st.markdown('<div class="section-hdr">🟢 PDH Breakout — BUY Signals</div>',
                unsafe_allow_html=True)
    if buys:
        for d in buys:
            st.markdown(f"""
            <div class="alert-card buy">
              <div>
                <span class="alert-sym" style="color:#00E676">{d['sym']}</span>
                &nbsp;<span class="alert-badge badge-buy">▲ BUY</span>
              </div>
              <div class="alert-price">₹ {d['close']:.2f}</div>
              <div class="alert-meta">PDH: {d['s_pdh']}</div>
              <div class="alert-meta">PDH%: {d['s_pdpct']}</div>
              <div class="alert-meta">RSI: {d['s_rsi']}  VWAP: {d['s_vwap']}</div>
              <div class="alert-meta">{d['s_dir']}</div>
            </div>""", unsafe_allow_html=True)
    else:
        st.markdown('<div class="no-signal">— No BUY signals found —</div>',
                    unsafe_allow_html=True)

    # SELL Alerts
    st.markdown('<div class="section-hdr">🔴 PDL Breakdown — SELL Signals</div>',
                unsafe_allow_html=True)
    if sells:
        for d in sells:
            st.markdown(f"""
            <div class="alert-card sell">
              <div>
                <span class="alert-sym" style="color:#FF1744">{d['sym']}</span>
                &nbsp;<span class="alert-badge badge-sell">▼ SELL</span>
              </div>
              <div class="alert-price">₹ {d['close']:.2f}</div>
              <div class="alert-meta">PDL: {d['s_pdl']}</div>
              <div class="alert-meta">PDL%: {d['s_pdpct']}</div>
              <div class="alert-meta">RSI: {d['s_rsi']}  VWAP: {d['s_vwap']}</div>
              <div class="alert-meta">{d['s_dir']}</div>
            </div>""", unsafe_allow_html=True)
    else:
        st.markdown('<div class="no-signal">— No SELL signals found —</div>',
                    unsafe_allow_html=True)

    # Download CSV
    if all_alerts:
        st.markdown("---")
        rows = [{
            "Symbol":    d["sym"],
            "Signal":    "BUY" if d["pdh_buy"] else "SELL",
            "Close":     d["close"],
            "PDH":       d["pdH"],
            "PDL":       d["pdL"],
            "PDH/PDL%":  d["s_pdpct"],
            "RSI":       d["s_rsi"],
            "VWAP":      d["s_vwap"],
            "Direction": d["s_dir"],
            "HTF":       htf,
            "ChartTF":   chart_tf,
        } for d in all_alerts]
        csv = pd.DataFrame(rows).to_csv(index=False).encode()
        ts  = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        st.download_button(
            "💾  Download Alerts CSV", csv,
            f"karma_alerts_{ts}.csv", "text/csv",
            use_container_width=True
        )

else:
    st.markdown("""
    <div class="no-signal" style="padding:80px">
      <div style="font-size:2.5rem; margin-bottom:14px">⬡</div>
      Use the sidebar to enable/disable each filter<br>
      then click <strong>▶ RUN SCAN</strong>
    </div>""", unsafe_allow_html=True)
