import streamlit as st, sys, os, math, datetime, pytz, pandas as pd
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils.scanner    import scan_symbol
from utils.indicators import compute_sma, compute_vwap, compute_rsi
from utils.stocks     import STOCKS
from utils.bg_scanner import BgScanner
from utils.history    import get_by_ticker

IST = pytz.timezone("Asia/Kolkata")
st.set_page_config(page_title="KARMA Dashboard", page_icon="🔍", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Exo+2:wght@700&display=swap');
html,[class*="css"]{font-family:'Share Tech Mono',monospace;}
h1,h2,h3{font-family:'Exo 2',sans-serif!important;font-weight:700!important;}
[data-testid="metric-container"]{background:#0D1117;border:1px solid #1C1C2E;border-radius:8px;padding:12px;}
.stButton>button{background:linear-gradient(135deg,#00E5FF11,#00E5FF33);
  border:1px solid #00E5FF55;color:#00E5FF;font-family:'Share Tech Mono',monospace;border-radius:6px;}
</style>""", unsafe_allow_html=True)

DEF = {"htf":"15m","use_body":True,"min_body":75.0,"max_body":80.0,
       "use_wick":True,"max_wick":20.0,"use_vol":True,"v_len":20,"v_mult":1.5,
       "use_pd_pct":True,"pd_pct":1.0,"use_rsi":True,"rsi_len":14,"use_vwap":True}
cfg = st.session_state.get("cfg", DEF.copy())

with st.sidebar:
    # ── Background Scan Status — TOP ───────────────────────────
    st.markdown("### 🔄 Background Scan")
    s = BgScanner.state()
    if s["running"]:
        pct = int(s["progress"]*100)
        st.markdown(f"**🟡 {pct}%** — `{s['current']}`")
        st.progress(s["progress"])
        st.caption(f'{s["scanned"]}/{s["total"]} stocks')
    elif s["done"]:
        bc = sum(1 for r in s["results"] if "BUY"  in r.get("signal",""))
        sc = sum(1 for r in s["results"] if "SELL" in r.get("signal",""))
        st.success(f"✅ 🟢{bc} BUY  🔴{sc} SELL")
        if s["scan_time"]: st.caption(s["scan_time"].strftime("%H:%M:%S IST"))
    else:
        st.info("No scan running — go to Scanner page")
    st.divider()

    st.markdown("### 🔍 Select Stock")
    tickers = sorted([s.replace(".NS","") for s in STOCKS])
    chosen  = st.selectbox("Ticker", tickers,
                           index=tickers.index("RELIANCE") if "RELIANCE" in tickers else 0)
    ticker  = chosen+".NS"

    st.markdown("### ⚙️ Filters")
    cfg["htf"]      = st.selectbox("HTF", ["1m","5m","15m","30m","60m","1d"],
                                   index=["1m","5m","15m","30m","60m","1d"].index(cfg.get("htf","15m")))
    cfg["use_body"] = st.checkbox("✅ Body % Filter", value=cfg.get("use_body",True), key="d_body")
    if cfg["use_body"]:
        d1,d2=st.columns([3,1])
        with d1: cfg["min_body"]=st.slider("Min Body%",50.0,95.0,float(cfg.get("min_body",75.0)),0.5,key="d_slminb")
        with d2: cfg["min_body"]=st.number_input("Min",50.0,95.0,float(cfg.get("min_body",75.0)),0.5,key="d_niminb",label_visibility="visible")
        d3,d4=st.columns([3,1])
        with d3: cfg["max_body"]=st.slider("Max Body%",55.0,99.0,float(cfg.get("max_body",80.0)),0.5,key="d_slmaxb")
        with d4: cfg["max_body"]=st.number_input("Max",55.0,99.0,float(cfg.get("max_body",80.0)),0.5,key="d_nimaxb",label_visibility="visible")
    cfg["use_wick"] = st.checkbox("✅ Wick % Filter", value=cfg.get("use_wick",True), key="d_wick")
    if cfg["use_wick"]:
        w1,w2=st.columns([3,1])
        with w1: cfg["max_wick"]=st.slider("Max Wick%",1.0,49.0,float(cfg.get("max_wick",20.0)),0.5,key="d_slwick")
        with w2: cfg["max_wick"]=st.number_input("Max",1.0,49.0,float(cfg.get("max_wick",20.0)),0.5,key="d_niwick",label_visibility="visible")
    cfg["use_vol"]  = st.checkbox("✅ Volume Filter",value=cfg.get("use_vol",True), key="d_vol")
    v1,v2=st.columns([3,1])
    with v1: cfg["v_len"]=st.slider("Vol MA Length",5,200,int(cfg.get("v_len",20)),key="d_slvlen")
    with v2: cfg["v_len"]=st.number_input("Len",5,200,int(cfg.get("v_len",20)),key="d_nivlen",label_visibility="visible")
    if cfg["use_vol"]:
        m1,m2=st.columns([3,1])
        with m1: cfg["v_mult"]=st.slider("Vol Mult",1.0,10.0,float(cfg.get("v_mult",1.5)),0.1,key="d_slvmult")
        with m2: cfg["v_mult"]=st.number_input("Mult",1.0,10.0,float(cfg.get("v_mult",1.5)),0.1,key="d_nivmult",label_visibility="visible")
    cfg["use_pd_pct"] = st.checkbox("✅ PDH/PDL% Filter",value=cfg.get("use_pd_pct",True),key="d_pd")
    if cfg["use_pd_pct"]:
        p1,p2=st.columns([3,1])
        with p1: cfg["pd_pct"]=st.slider("PDH/PDL%",0.1,10.0,float(cfg.get("pd_pct",1.0)),0.1,key="d_slpd")
        with p2: cfg["pd_pct"]=st.number_input("Pct",0.1,10.0,float(cfg.get("pd_pct",1.0)),0.1,key="d_nipd",label_visibility="visible")
    cfg["use_rsi"]  = st.checkbox("✅ RSI", value=cfg.get("use_rsi",True), key="d_rsi")
    if cfg["use_rsi"]:
        r1,r2=st.columns([3,1])
        with r1: cfg["rsi_len"]=st.slider("RSI Length",2,50,int(cfg.get("rsi_len",14)),key="d_slrsi")
        with r2: cfg["rsi_len"]=st.number_input("Len",2,50,int(cfg.get("rsi_len",14)),key="d_nirsi",label_visibility="visible")
    cfg["use_vwap"] = st.checkbox("✅ VWAP",value=cfg.get("use_vwap",True), key="d_vwap")
    run = st.button("🚀 Scan This Stock", use_container_width=True)
    st.session_state["cfg"] = cfg

prev = st.session_state.get("dash_ticker")
if run or prev != ticker:
    st.session_state["dash_ticker"] = ticker
    with st.spinner(f"Scanning {ticker}..."):
        st.session_state["dash_result"] = scan_symbol(ticker, cfg)

if "dash_result" not in st.session_state:
    st.info("Select a stock and click **Scan This Stock**")
    st.stop()

r = st.session_state["dash_result"]

# ── Signal banner ─────────────────────────────────────────────
sig = r["signal"]
is_buy  = "BUY"  in sig
is_sell = "SELL" in sig
bg  = "#003344" if is_buy else "#330E00" if is_sell else "#111"
col = "#00E5FF" if is_buy else "#FF6D00" if is_sell else "#444"
st.markdown(f'<div style="background:{bg};border:2px solid {col}44;border-radius:10px;'
            f'padding:16px;text-align:center;font-size:1.4rem;font-weight:bold;'
            f'letter-spacing:3px;color:{col};font-family:monospace;margin-bottom:20px;">'
            f'{"🟢" if is_buy else "🔴" if is_sell else "⚪"} {sig.strip()}</div>',
            unsafe_allow_html=True)

# ── Pine Script dashboard table replica ───────────────────────
st.markdown(f"""
<div style="background:#0A0A0F;border:1px solid #1C1C2E;border-radius:10px;
     padding:4px;margin-bottom:20px;">
  <div style="background:#1A1A2E;border-radius:8px;padding:12px;text-align:center;
       color:#fff;font-family:'Share Tech Mono',monospace;letter-spacing:2px;
       font-weight:bold;margin-bottom:4px;">
    PDH / PDL BREAKOUT SCANNER — {ticker.replace('.NS','')}
  </div>""", unsafe_allow_html=True)

def row(label, value, vc):
    return (f"<div style='display:flex;justify-content:space-between;padding:8px 16px;"
            f"border-bottom:1px solid #111;font-family:monospace;'>"
            f"<span style='color:#888;font-size:.85rem'>{label}</span>"
            f"<span style='color:{vc};font-weight:bold'>{value}</span></div>")

is_bull = r["htf_dir"]=="BULLISH"
is_bear = r["htf_dir"]=="BEARISH"
rel_dist= r["pdh_dist_pct"] if is_bull else r["pdl_dist_pct"]
pdpct_ok= rel_dist >= cfg["pd_pct"] if cfg["use_pd_pct"] else True
b_ok_c  = "#00E676" if (r["body_ok"] or not cfg["use_body"]) else "#FF1744"
w_ok_c  = "#00E676" if (r["wick_ok"] or not cfg["use_wick"]) else "#FF1744"
v_ok_c  = "#00E676" if (r["vol_ok"]  or not cfg["use_vol"])  else "#FF1744"
pd_c    = "#00E676" if pdpct_ok else "#FF1744"
dir_c   = "#00E676" if is_bull else "#FF1744" if is_bear else "#AAAAAA"

body_v = f"{r['body_pct']:.1f}%  [{cfg['min_body']}-{cfg['max_body']}%]" if cfg["use_body"] else f"{r['body_pct']:.1f}%  (filter OFF)"
wick_v = f"{r['wick_pct']:.1f}%  [max {cfg['max_wick']}%]" if cfg["use_wick"] else f"{r['wick_pct']:.1f}%  (filter OFF)"
vol_v  = f"{r['vol_ratio']:.2f}x  [>= {cfg['v_mult']}x]" if cfg["use_vol"]  else f"{r['vol_ratio']:.2f}x  (filter OFF)"
pd_v   = (f"{rel_dist:.1f}%  (min {cfg['pd_pct']}%)" if cfg["use_pd_pct"] else "disabled")

rsi_val  = f"{r['rsi']:.1f}" if not math.isnan(r.get("rsi",float("nan"))) else "disabled"
vwap_val = (f"{r['vwap']:.2f}  ({'above' if r['close']>=r['vwap'] else 'below'})"
            if not math.isnan(r.get("vwap",float("nan"))) else "disabled")
cvol_k   = f"{r['cur_vol']/1000:.1f}K" if not math.isnan(r.get("cur_vol",float("nan"))) else "n/a"
cvol_pct = (f"  ({r['cur_vol']/r['cur_vol_ma']*100:.0f}% avg)"
            if not math.isnan(r.get("cur_vol_ma",float("nan"))) and r["cur_vol_ma"]>0 else "")
cvol_c   = "#00E676" if (not math.isnan(r.get("cur_vol",float("nan"))) and
                         not math.isnan(r.get("cur_vol_ma",float("nan"))) and
                         r["cur_vol"]>=r["cur_vol_ma"]) else "#FFD600"
rsi_c    = ("#FF1744" if not math.isnan(r.get("rsi",float("nan"))) and r["rsi"]>=70
            else "#00E676" if not math.isnan(r.get("rsi",float("nan"))) and r["rsi"]<=30
            else "#40C4FF")
vwap_c   = ("#00E676" if not math.isnan(r.get("vwap",float("nan"))) and r["close"]>=r["vwap"]
            else "#FF1744")

html = (row(f"HTF Scan", f"{cfg['htf']}  |  Scanner", "#40C4FF") +
        row(f"Body %", body_v, b_ok_c) +
        row(f"Wick %", wick_v, w_ok_c) +
        row(f"Volume", vol_v, v_ok_c) +
        row("HTF Direction", ("📈 " if is_bull else "📉 " if is_bear else "➡ ")+r["htf_dir"], dir_c) +
        row("PDH", f"₹{r['pdh']:.2f}" if not math.isnan(r["pdh"]) else "n/a", "#00E676") +
        row("PDL", f"₹{r['pdl']:.2f}" if not math.isnan(r["pdl"]) else "n/a", "#FF1744") +
        row(f"PDH/PDL %  [>= {cfg['pd_pct']}%]", pd_v, pd_c))

sig_c   = "#00E5FF" if is_buy else "#FF6D00" if is_sell else "#444"
sig_bg  = "#003344" if is_buy else "#330E00" if is_sell else "#111"
html += (f"<div style='text-align:center;padding:10px;background:{sig_bg};"
         f"font-family:monospace;font-weight:bold;font-size:1rem;color:{sig_c};"
         f"border-bottom:1px solid #111'>{sig.strip()}</div>")
html += (f"<div style='text-align:center;padding:6px;color:#666;font-size:.8rem;"
         f"letter-spacing:2px;border-bottom:1px solid #111'>-- LIVE INDICATORS --</div>" +
         row("Cur Volume", cvol_k+cvol_pct, cvol_c) +
         row(f"RSI ({cfg['rsi_len']})", rsi_val, rsi_c) +
         row("VWAP", vwap_val, vwap_c))

st.markdown(html+"</div>", unsafe_allow_html=True)

# ── Metrics ───────────────────────────────────────────────────
st.markdown("### 📊 Key Metrics")
m1,m2,m3,m4,m5,m6 = st.columns(6)
m1.metric("LTP ₹",    f"{r['close']:.2f}"  if not math.isnan(r["close"]) else "n/a")
m2.metric("PDH ₹",    f"{r['pdh']:.2f}"   if not math.isnan(r["pdh"])   else "n/a")
m3.metric("PDL ₹",    f"{r['pdl']:.2f}"   if not math.isnan(r["pdl"])   else "n/a")
m4.metric("VWAP ₹",   f"{r['vwap']:.2f}"  if not math.isnan(r.get("vwap",float("nan"))) else "n/a")
m5.metric("RSI",      f"{r['rsi']:.1f}"   if not math.isnan(r.get("rsi",float("nan")))  else "n/a")
m6.metric("Vol Ratio",f"{r['vol_ratio']:.2f}x")

# ── Candlestick chart ─────────────────────────────────────────
st.markdown("### 🕯 HTF Chart")
try:
    from utils.scanner import PERIOD_MAP, _flat
    period  = PERIOD_MAP.get(cfg["htf"],"60d")
    cdf = yf.download(ticker, period=period, interval=cfg["htf"],
                      auto_adjust=True, progress=False)
    if cdf is not None and len(cdf)>10:
        cdf = _flat(cdf); cdf.dropna(inplace=True); cdf = cdf.tail(100)
        fig = make_subplots(rows=2,cols=1,shared_xaxes=True,row_heights=[.7,.3],vertical_spacing=.04)
        fig.add_trace(go.Candlestick(x=cdf.index,open=cdf["Open"],high=cdf["High"],
                                     low=cdf["Low"],close=cdf["Close"],
                                     increasing_line_color="#00E676",decreasing_line_color="#FF1744",
                                     name="Price"),row=1,col=1)
        if not math.isnan(r["pdh"]):
            fig.add_hline(y=r["pdh"],line_dash="dash",line_color="#00E676",line_width=1.5,
                          annotation_text=f"PDH {r['pdh']:.2f}",annotation_font_color="#00E676",row=1,col=1)
        if not math.isnan(r["pdl"]):
            fig.add_hline(y=r["pdl"],line_dash="dash",line_color="#FF1744",line_width=1.5,
                          annotation_text=f"PDL {r['pdl']:.2f}",annotation_font_color="#FF1744",row=1,col=1)
        vol_c = ["#00E676" if c>=o else "#FF1744" for c,o in zip(cdf["Close"],cdf["Open"])]
        fig.add_trace(go.Bar(x=cdf.index,y=cdf["Volume"],marker_color=vol_c,opacity=.6,name="Vol"),row=2,col=1)
        vma = compute_sma(cdf["Volume"],cfg["v_len"])
        fig.add_trace(go.Scatter(x=cdf.index,y=vma,line=dict(color="#40C4FF",width=1.5),
                                 name=f"VolMA({cfg['v_len']})"),row=2,col=1)
        fig.update_layout(template="plotly_dark",paper_bgcolor="#070710",plot_bgcolor="#0A0A0F",
                          xaxis_rangeslider_visible=False,height=500,
                          margin=dict(l=0,r=0,t=20,b=0),
                          font=dict(family="Share Tech Mono,monospace",color="#888"),
                          legend=dict(orientation="h",yanchor="bottom",y=1.02))
        fig.update_xaxes(gridcolor="#1C1C2E"); fig.update_yaxes(gridcolor="#1C1C2E")
        st.plotly_chart(fig, use_container_width=True)
except Exception as e:
    st.warning(f"Chart error: {e}")

# ── HTF History for this stock (last 60 bars) ─────────────────
st.markdown("### 📋 HTF Bar History (Last 60 Bars)")
if r.get("history"):
    hdf = pd.DataFrame(r["history"])
    def hl_hist(row):
        if row["signal"]=="BUY":  return ["color:#00E5FF"]*len(row)
        if row["signal"]=="SELL": return ["color:#FF6D00"]*len(row)
        return [""]*len(row)
    st.dataframe(hdf.style.apply(hl_hist,axis=1), use_container_width=True, hide_index=True)
else:
    st.info("No history data")

# ── Past signals for this ticker ─────────────────────────────
past = get_by_ticker(ticker)
if past:
    st.markdown(f"### 📜 Past Alerts for {chosen} ({len(past)} records)")
    pdf = pd.DataFrame(past)[["date","time","signal","close","pdh","pdl","body_pct","wick_pct","vol_ratio","rsi","htf"]]
    st.dataframe(pdf, use_container_width=True, hide_index=True)

if r.get("error"):
    st.error(f"Error: {r['error']}")
st.caption(f"Scanned at {datetime.datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST')}")
