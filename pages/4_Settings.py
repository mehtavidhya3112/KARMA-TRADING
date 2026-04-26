import streamlit as st, sys, os, pandas as pd
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.bg_scanner import BgScanner

st.set_page_config(page_title="KARMA Settings", page_icon="⚙️", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Exo+2:wght@700&display=swap');
html,[class*="css"]{font-family:'Share Tech Mono',monospace;}
h1,h2,h3{font-family:'Exo 2',sans-serif!important;font-weight:700!important;}
.stButton>button{background:linear-gradient(135deg,#00E5FF11,#00E5FF33);
  border:1px solid #00E5FF55;color:#00E5FF;font-family:'Share Tech Mono',monospace;border-radius:6px;}
.input-row{background:#0D1117;border:1px solid #1C1C2E;border-radius:8px;padding:10px 14px;margin-bottom:8px;}
</style>""", unsafe_allow_html=True)

with st.sidebar:
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

st.markdown("""
<div style="background:linear-gradient(135deg,#0D1117,#080815);
     border:1px solid #00E5FF33;border-radius:10px;padding:16px 24px;margin-bottom:24px;">
  <h2 style="color:#00E5FF;margin:0;letter-spacing:2px;">⚙️ SCANNER SETTINGS</h2>
  <p style="color:#666;margin:4px 0 0;">
    All Pine Script inputs · checkbox to enable/disable each filter ·
    slider OR type exact value in the box
  </p>
</div>""", unsafe_allow_html=True)

DEF = {"htf":"15m","use_body":True,"min_body":75.0,"max_body":80.0,
       "use_wick":True,"max_wick":20.0,"use_vol":True,"v_len":20,"v_mult":1.5,
       "use_pd_pct":True,"pd_pct":1.0,"use_rsi":True,"rsi_len":14,"use_vwap":True}
cfg = st.session_state.get("cfg", DEF.copy())

col1, col2 = st.columns(2)

with col1:
    # ── Timeframe ─────────────────────────────────────────────
    st.markdown("### 📅 Timeframe  `i_htf`")
    cfg["htf"] = st.selectbox("HTF Timeframe",
        ["1m","5m","15m","30m","60m","1h","1d"],
        index=["1m","5m","15m","30m","60m","1h","1d"].index(cfg.get("htf","15m")),
        help="Pine default: '' (same as chart TF)", key="gs_htf")

    # ── Body Filter ───────────────────────────────────────────
    st.markdown("### 📐 Body % Filter  `i_useBody · i_minB · i_maxB`")
    cfg["use_body"] = st.checkbox("✅ Enable Body % Filter  `i_useBody`",
        value=cfg.get("use_body",True), key="gs_ubody",
        help="When unchecked, all candle body sizes pass the filter")
    if cfg["use_body"]:
        st.caption("Slide or type an exact value:")
        r1c1, r1c2 = st.columns([3,1])
        with r1c1:
            cfg["min_body"] = st.slider("Min Body %  `i_minB`", 50.0, 95.0,
                float(cfg.get("min_body",75.0)), 0.5, key="gs_slminb",
                help="Pine default: 75.0")
        with r1c2:
            cfg["min_body"] = st.number_input("Min", 50.0, 95.0,
                float(cfg.get("min_body",75.0)), 0.5, key="gs_niminb",
                label_visibility="visible")
        r2c1, r2c2 = st.columns([3,1])
        with r2c1:
            cfg["max_body"] = st.slider("Max Body %  `i_maxB`", 55.0, 99.0,
                float(cfg.get("max_body",80.0)), 0.5, key="gs_slmaxb",
                help="Pine default: 80.0")
        with r2c2:
            cfg["max_body"] = st.number_input("Max", 55.0, 99.0,
                float(cfg.get("max_body",80.0)), 0.5, key="gs_nimaxb",
                label_visibility="visible")
    else:
        cfg["min_body"] = DEF["min_body"]; cfg["max_body"] = DEF["max_body"]
        st.info("Filter OFF — all candle body sizes accepted")

    # ── Wick Filter ───────────────────────────────────────────
    st.markdown("### 📐 Wick % Filter  `i_useWick · i_maxW`")
    cfg["use_wick"] = st.checkbox("✅ Enable Wick % Filter  `i_useWick`",
        value=cfg.get("use_wick",True), key="gs_uwick",
        help="When unchecked, all wick sizes pass the filter")
    if cfg["use_wick"]:
        st.caption("Slide or type an exact value:")
        wc1, wc2 = st.columns([3,1])
        with wc1:
            cfg["max_wick"] = st.slider("Max Wick %  `i_maxW`", 1.0, 49.0,
                float(cfg.get("max_wick",20.0)), 0.5, key="gs_slwick",
                help="Pine default: 20.0")
        with wc2:
            cfg["max_wick"] = st.number_input("Max", 1.0, 49.0,
                float(cfg.get("max_wick",20.0)), 0.5, key="gs_niwick",
                label_visibility="visible")
    else:
        cfg["max_wick"] = DEF["max_wick"]
        st.info("Filter OFF — all wick sizes accepted")

    # ── Volume Filter ─────────────────────────────────────────
    st.markdown("### 📊 Volume Filter  `i_useVol · i_vlen · i_vmult`")
    cfg["use_vol"] = st.checkbox("✅ Enable Volume Filter  `i_useVol`",
        value=cfg.get("use_vol",True), key="gs_uvol",
        help="When unchecked, any volume level passes")
    st.caption("Vol MA Length (always active):")
    vc1, vc2 = st.columns([3,1])
    with vc1:
        cfg["v_len"] = st.slider("Vol MA Length  `i_vlen`", 5, 200,
            int(cfg.get("v_len",20)), key="gs_slvlen",
            help="Pine default: 20")
    with vc2:
        cfg["v_len"] = st.number_input("Len", 5, 200,
            int(cfg.get("v_len",20)), key="gs_nivlen",
            label_visibility="visible")
    if cfg["use_vol"]:
        st.caption("Volume multiplier:")
        vm1, vm2 = st.columns([3,1])
        with vm1:
            cfg["v_mult"] = st.slider("Volume >= X × Avg  `i_vmult`", 1.0, 10.0,
                float(cfg.get("v_mult",1.5)), 0.1, key="gs_slvmult",
                help="Pine default: 1.5")
        with vm2:
            cfg["v_mult"] = st.number_input("Mult", 1.0, 10.0,
                float(cfg.get("v_mult",1.5)), 0.1, key="gs_nivmult",
                label_visibility="visible")
    else:
        cfg["v_mult"] = DEF["v_mult"]
        st.info("Filter OFF — any volume accepted")

with col2:
    # ── PDH/PDL % Filter ──────────────────────────────────────
    st.markdown("### 📏 PDH/PDL % Filter  `i_usePDPct · i_pdPct`")
    cfg["use_pd_pct"] = st.checkbox("✅ Enable PDH/PDL % Filter  `i_usePDPct`",
        value=cfg.get("use_pd_pct",True), key="gs_upd",
        help="BUY: close >= PDH×(1+%/100)  SELL: close <= PDL×(1-%/100)")
    if cfg["use_pd_pct"]:
        st.caption("Slide or type an exact value:")
        pd1, pd2 = st.columns([3,1])
        with pd1:
            cfg["pd_pct"] = st.slider("Min % above PDH / below PDL  `i_pdPct`",
                0.1, 10.0, float(cfg.get("pd_pct",1.0)), 0.1, key="gs_slpd",
                help="Pine default: 1.0")
        with pd2:
            cfg["pd_pct"] = st.number_input("Pct", 0.1, 10.0,
                float(cfg.get("pd_pct",1.0)), 0.1, key="gs_nipd",
                label_visibility="visible")
    else:
        cfg["pd_pct"] = DEF["pd_pct"]
        st.info("Filter OFF — any breakout above/below PDH/PDL counts")

    # ── RSI ───────────────────────────────────────────────────
    st.markdown("### 📈 RSI  `i_useRSI · i_rsiLen`")
    cfg["use_rsi"] = st.checkbox("✅ Enable RSI  `i_useRSI`",
        value=cfg.get("use_rsi",True), key="gs_ursi",
        help="Wilder RSI shown in dashboard. Does not filter signals.")
    if cfg["use_rsi"]:
        st.caption("Slide or type an exact value:")
        rr1, rr2 = st.columns([3,1])
        with rr1:
            cfg["rsi_len"] = st.slider("RSI Length  `i_rsiLen`", 2, 50,
                int(cfg.get("rsi_len",14)), key="gs_slrsi",
                help="Pine default: 14")
        with rr2:
            cfg["rsi_len"] = st.number_input("Len", 2, 50,
                int(cfg.get("rsi_len",14)), key="gs_nirsi",
                label_visibility="visible")
    else:
        cfg["rsi_len"] = DEF["rsi_len"]
        st.info("RSI disabled — shows n/a in results")

    # ── VWAP ─────────────────────────────────────────────────
    st.markdown("### 📈 VWAP  `i_useVWAP`")
    cfg["use_vwap"] = st.checkbox("✅ Enable VWAP  `i_useVWAP`",
        value=cfg.get("use_vwap",True), key="gs_uvwap",
        help="Session VWAP shown in dashboard. Does not filter signals.")
    if not cfg["use_vwap"]:
        st.info("VWAP disabled — shows n/a in results")

    # ── Pine Script defaults reference ────────────────────────
    st.markdown("### 📋 Pine Script Defaults")
    st.code("""i_htf      = ""       // chart TF
i_useBody  = true
i_minB     = 75.0     // Min Body %
i_maxB     = 80.0     // Max Body %
i_useWick  = true
i_maxW     = 20.0     // Max Wick %
i_useVol   = true
i_vlen     = 20       // Vol MA length
i_vmult    = 1.5      // Vol multiplier
i_usePDPct = true
i_pdPct    = 1.0      // PDH/PDL % filter
i_useRSI   = true
i_rsiLen   = 14       // RSI length
i_useVWAP  = true""", language="pine")

st.divider()
sc, rc, _ = st.columns([1,1,4])
with sc:
    if st.button("💾 Save Settings", use_container_width=True):
        st.session_state["cfg"] = cfg
        st.success("✅ Saved! Applied to Scanner & Dashboard.")
with rc:
    if st.button("🔄 Reset to Defaults", use_container_width=True):
        st.session_state["cfg"] = DEF.copy()
        st.success("✅ Reset to Pine Script defaults.")
        st.rerun()

# Config summary
st.markdown("### 📋 Current Configuration")
rows = [
    ["HTF","cfg['htf']",cfg["htf"],"i_htf"],
    ["Body Filter","use_body","✅ ON" if cfg["use_body"] else "❌ OFF","i_useBody"],
    ["Min Body %","min_body",f"{cfg['min_body']}%" if cfg["use_body"] else "—","i_minB"],
    ["Max Body %","max_body",f"{cfg['max_body']}%" if cfg["use_body"] else "—","i_maxB"],
    ["Wick Filter","use_wick","✅ ON" if cfg["use_wick"] else "❌ OFF","i_useWick"],
    ["Max Wick %","max_wick",f"{cfg['max_wick']}%" if cfg["use_wick"] else "—","i_maxW"],
    ["Volume Filter","use_vol","✅ ON" if cfg["use_vol"] else "❌ OFF","i_useVol"],
    ["Vol MA Length","v_len",str(cfg["v_len"]),"i_vlen"],
    ["Vol Multiplier","v_mult",f"{cfg['v_mult']}x" if cfg["use_vol"] else "—","i_vmult"],
    ["PDH/PDL% Filter","use_pd_pct","✅ ON" if cfg["use_pd_pct"] else "❌ OFF","i_usePDPct"],
    ["PDH/PDL% Min","pd_pct",f"{cfg['pd_pct']}%" if cfg["use_pd_pct"] else "—","i_pdPct"],
    ["RSI","use_rsi","✅ ON" if cfg["use_rsi"] else "❌ OFF","i_useRSI"],
    ["RSI Length","rsi_len",str(cfg["rsi_len"]) if cfg["use_rsi"] else "—","i_rsiLen"],
    ["VWAP","use_vwap","✅ ON" if cfg["use_vwap"] else "❌ OFF","i_useVWAP"],
]
st.dataframe(pd.DataFrame(rows, columns=["Parameter","Key","Value","Pine Variable"]),
             use_container_width=True, hide_index=True)
