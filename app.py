import streamlit as st, sys, os
sys.path.insert(0, os.path.dirname(__file__))

st.set_page_config(
    page_title="KARMA PA Scanner",
    page_icon="🔥", layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Exo+2:wght@700&display=swap');
html,[class*="css"]{font-family:'Share Tech Mono',monospace;}
h1,h2,h3{font-family:'Exo 2',sans-serif!important;font-weight:700!important;}
[data-testid="metric-container"]{background:#0D1117;border:1px solid #1C1C2E;border-radius:8px;padding:12px;}
.stButton>button{background:linear-gradient(135deg,#00E5FF11,#00E5FF33);
  border:1px solid #00E5FF55;color:#00E5FF;font-family:'Share Tech Mono',monospace;
  border-radius:6px;transition:all .2s;}
.stButton>button:hover{background:#00E5FF22;box-shadow:0 0 10px #00E5FF44;}
</style>
""", unsafe_allow_html=True)

# ── Background scan status banner (shows on home if scan running) ──
try:
    from utils.bg_scanner import BgScanner
    s = BgScanner.state()
    if s["running"]:
        pct = int(s["progress"]*100)
        st.info(f"🔄 Background scan running: **{s['current']}** — {s['scanned']}/{s['total']} stocks ({pct}%)")
        st.progress(s["progress"])
    elif s["done"] and s["scan_time"]:
        buy_c  = sum(1 for r in s["results"] if "BUY"  in r.get("signal",""))
        sell_c = sum(1 for r in s["results"] if "SELL" in r.get("signal",""))
        st.success(f"✅ Last scan done at {s['scan_time'].strftime('%H:%M:%S IST')} — 🟢 {buy_c} BUY  |  🔴 {sell_c} SELL")
except: pass

st.markdown("""
<div style="background:linear-gradient(135deg,#0D1117,#0A0A1F);
     border:1px solid #00E5FF33;border-radius:12px;padding:24px 32px;margin-bottom:24px;">
  <h1 style="color:#00E5FF;margin:0;letter-spacing:3px;">🔥 KARMA PRICE ACTION</h1>
  <h2 style="color:#ffffff;margin:6px 0 0;font-size:1.2rem;letter-spacing:2px;">PDH / PDL BREAKOUT SCANNER</h2>
  <p style="color:#666;margin:8px 0 0;">206 NSE Stocks · Exact Pine Script Logic · Background Scan · Live Alerts · Full History</p>
</div>
""", unsafe_allow_html=True)

c1,c2,c3,c4 = st.columns(4)
with c1:
    st.markdown("### 📊 Scanner\nScan 206 NSE stocks in background. BUY/SELL signals with all Pine Script filters.")
    st.page_link("pages/1_Scanner.py", label="▶ Open Scanner", icon="📊")
with c2:
    st.markdown("### 🔍 Dashboard\nSingle stock deep-dive. Full Pine Script dashboard + candlestick chart.")
    st.page_link("pages/2_Dashboard.py", label="▶ Open Dashboard", icon="🔍")
with c3:
    st.markdown("### 📜 History\nSignal alerts + full scan snapshots for all 206 stocks — all in one page.")
    st.page_link("pages/3_History.py", label="▶ Open History", icon="📜")
with c4:
    st.markdown("### ⚙️ Settings\nAll Pine Script inputs — toggle every filter on/off with sliders.")
    st.page_link("pages/4_Settings.py", label="▶ Open Settings", icon="⚙️")

st.divider()
col_buy, col_sell = st.columns(2)
with col_buy:
    st.markdown("""**🟢 BUY Signal — PDH Breakout**
- HTF candle Bullish (close > open)
- Body % in [min_body, max_body]
- Wick % ≤ max_wick
- Volume ≥ v_mult × SMA(vol, 20)
- Close ≥ PDH × (1 + pd_pct/100)
- NOT the 9:15 AM IST candle""")
with col_sell:
    st.markdown("""**🔴 SELL Signal — PDL Breakdown**
- HTF candle Bearish (close < open)
- Body % in [min_body, max_body]
- Wick % ≤ max_wick
- Volume ≥ v_mult × SMA(vol, 20)
- Close ≤ PDL × (1 − pd_pct/100)
- NOT the 9:15 AM IST candle""")
st.caption("Data: Yahoo Finance · Timezone: IST · © KARMA PA Scanner")
