import streamlit as st, sys, os, math, datetime, time, pytz, pandas as pd
import streamlit.components.v1 as components
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.bg_scanner import BgScanner
from utils.stocks     import PRESETS
from utils.history    import get_today

IST = pytz.timezone("Asia/Kolkata")
st.set_page_config(page_title="KARMA Scanner", page_icon="📊", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Exo+2:wght@700&display=swap');
html,[class*="css"]{font-family:'Share Tech Mono',monospace;}
h1,h2,h3{font-family:'Exo 2',sans-serif!important;font-weight:700!important;}
[data-testid="metric-container"]{background:#0D1117;border:1px solid #1C1C2E;border-radius:8px;padding:12px;}
.stButton>button{background:linear-gradient(135deg,#00E5FF11,#00E5FF33);
  border:1px solid #00E5FF55;color:#00E5FF;font-family:'Share Tech Mono',monospace;border-radius:6px;}
.pulse{display:inline-block;width:10px;height:10px;border-radius:50%;background:#00E676;
  animation:pulse 1.2s infinite;margin-right:8px;vertical-align:middle;}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1);}50%{opacity:.4;transform:scale(1.3);}}
.input-group{background:#0D1117;border:1px solid #1C1C2E;border-radius:8px;padding:10px 14px;margin-bottom:8px;}
</style>
""", unsafe_allow_html=True)

# Browser notification permission request (only components.html executes JS)
components.html("""
<script>
if (typeof window._karmaPerm === 'undefined') {
    window._karmaPerm = true;
    if ("Notification" in window && Notification.permission === "default") {
        Notification.requestPermission();
    }
}
</script>
""", height=0)

def fire_notification(ticker, signal, close_price, play_sound=True, push_notif=True):
    is_buy = "BUY" in signal
    icon   = "🟢" if is_buy else "🔴"
    freq   = 880  if is_buy else 440
    title  = f"KARMA {'BUY' if is_buy else 'SELL'}: {ticker}"
    body   = f"{'PDH Breakout' if is_buy else 'PDL Breakdown'} @ Rs.{close_price}"
    # Streamlit toast — always works
    st.toast(f"{icon} {signal.strip()} — {ticker} @ Rs.{close_price}", icon=icon)
    # Browser push + beep — needs components.html
    sound_js = f"""
  try{{
    var ctx=new(window.AudioContext||window.webkitAudioContext)();
    var o=ctx.createOscillator(),g=ctx.createGain();
    o.connect(g);g.connect(ctx.destination);
    o.type='sine';o.frequency.value={freq};
    g.gain.setValueAtTime(0.5,ctx.currentTime);
    g.gain.exponentialRampToValueAtTime(0.001,ctx.currentTime+0.8);
    o.start(ctx.currentTime);o.stop(ctx.currentTime+0.8);
  }}catch(e){{}}""" if play_sound else ""
    push_js = f"""
  var t="{title}",op={{body:"{body}"}};
  if("Notification" in window){{
    if(Notification.permission==="granted"){{new Notification(t,op);}}
    else if(Notification.permission!=="denied"){{
      Notification.requestPermission().then(function(p){{if(p==="granted")new Notification(t,op);}});
    }}
  }}""" if push_notif else ""
    components.html(f"<script>(function(){{{sound_js}{push_js}}})();</script>", height=0)

# ── Config defaults ────────────────────────────────────────────
DEF = {"htf":"15m","use_body":True,"min_body":75.0,"max_body":80.0,
       "use_wick":True,"max_wick":20.0,"use_vol":True,"v_len":20,"v_mult":1.5,
       "use_pd_pct":True,"pd_pct":1.0,"use_rsi":True,"rsi_len":14,"use_vwap":True}
cfg = st.session_state.get("cfg", DEF.copy())

# ══════════════════════════════════════════════════════════════
# SIDEBAR — all inputs: checkbox + slider + number_input
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    # ── Background Scan Status — TOP ───────────────────────────
    st.markdown("### 🔄 Background Scan")
    _s = BgScanner.state()
    if _s["running"]:
        _pct = int(_s["progress"]*100)
        st.markdown(f'**🟡 {_pct}%** — `{_s["current"]}`')
        st.progress(_s["progress"])
        st.caption(f'{_s["scanned"]}/{_s["total"]} stocks')
    elif _s["done"]:
        _bc = sum(1 for r in _s["results"] if "BUY"  in r.get("signal",""))
        _sc = sum(1 for r in _s["results"] if "SELL" in r.get("signal",""))
        st.success(f"✅ 🟢{_bc} BUY  🔴{_sc} SELL")
        if _s["scan_time"]: st.caption(_s["scan_time"].strftime("%H:%M:%S IST"))
    else:
        st.info("Click Start Scan below")
    st.divider()

    st.markdown("## ⚙️ Filter Settings")

    # ── Timeframe ──────────────────────────────────────────────
    st.markdown("#### 📅 Timeframe")
    cfg["htf"] = st.selectbox("HTF Timeframe",
        ["1m","5m","15m","30m","60m","1d"],
        index=["1m","5m","15m","30m","60m","1d"].index(cfg.get("htf","15m")),
        key="sc_htf")

    st.markdown("---")

    # ── Body Filter ────────────────────────────────────────────
    st.markdown("#### 📐 Body % Filter")
    cfg["use_body"] = st.checkbox("✅ Enable Body % Filter",
                                  value=cfg.get("use_body", True), key="cb_body")
    if cfg["use_body"]:
        c1, c2 = st.columns([3,1])
        with c1:
            cfg["min_body"] = st.slider("Min Body %", 50.0, 95.0,
                                        float(cfg.get("min_body",75.0)), 0.5, key="sl_minb")
        with c2:
            cfg["min_body"] = st.number_input("", 50.0, 95.0,
                                              float(cfg.get("min_body",75.0)), 0.5,
                                              key="ni_minb", label_visibility="collapsed")
        c3, c4 = st.columns([3,1])
        with c3:
            cfg["max_body"] = st.slider("Max Body %", 55.0, 99.0,
                                        float(cfg.get("max_body",80.0)), 0.5, key="sl_maxb")
        with c4:
            cfg["max_body"] = st.number_input("", 55.0, 99.0,
                                              float(cfg.get("max_body",80.0)), 0.5,
                                              key="ni_maxb", label_visibility="collapsed")
    else:
        st.caption("Filter OFF — all body sizes pass")

    st.markdown("---")

    # ── Wick Filter ────────────────────────────────────────────
    st.markdown("#### 📐 Wick % Filter")
    cfg["use_wick"] = st.checkbox("✅ Enable Wick % Filter",
                                  value=cfg.get("use_wick", True), key="cb_wick")
    if cfg["use_wick"]:
        c1, c2 = st.columns([3,1])
        with c1:
            cfg["max_wick"] = st.slider("Max Wick %", 1.0, 49.0,
                                        float(cfg.get("max_wick",20.0)), 0.5, key="sl_wick")
        with c2:
            cfg["max_wick"] = st.number_input("", 1.0, 49.0,
                                              float(cfg.get("max_wick",20.0)), 0.5,
                                              key="ni_wick", label_visibility="collapsed")
    else:
        st.caption("Filter OFF — all wick sizes pass")

    st.markdown("---")

    # ── Volume Filter ──────────────────────────────────────────
    st.markdown("#### 📊 Volume Filter")
    cfg["use_vol"] = st.checkbox("✅ Enable Volume Filter",
                                 value=cfg.get("use_vol", True), key="cb_vol")
    c1, c2 = st.columns([3,1])
    with c1:
        cfg["v_len"] = st.slider("Vol MA Length", 5, 200,
                                 int(cfg.get("v_len",20)), key="sl_vlen")
    with c2:
        cfg["v_len"] = st.number_input("", 5, 200,
                                       int(cfg.get("v_len",20)),
                                       key="ni_vlen", label_visibility="collapsed")
    if cfg["use_vol"]:
        c3, c4 = st.columns([3,1])
        with c3:
            cfg["v_mult"] = st.slider("Vol >= X × Avg", 1.0, 10.0,
                                      float(cfg.get("v_mult",1.5)), 0.1, key="sl_vmult")
        with c4:
            cfg["v_mult"] = st.number_input("", 1.0, 10.0,
                                            float(cfg.get("v_mult",1.5)), 0.1,
                                            key="ni_vmult", label_visibility="collapsed")
    else:
        st.caption("Filter OFF — any volume passes")

    st.markdown("---")

    # ── PDH/PDL % Filter ───────────────────────────────────────
    st.markdown("#### 📏 PDH/PDL % Filter")
    cfg["use_pd_pct"] = st.checkbox("✅ Enable PDH/PDL % Filter",
                                    value=cfg.get("use_pd_pct", True), key="cb_pd")
    if cfg["use_pd_pct"]:
        c1, c2 = st.columns([3,1])
        with c1:
            cfg["pd_pct"] = st.slider("Min % above PDH / below PDL", 0.1, 10.0,
                                      float(cfg.get("pd_pct",1.0)), 0.1, key="sl_pd")
        with c2:
            cfg["pd_pct"] = st.number_input("", 0.1, 10.0,
                                            float(cfg.get("pd_pct",1.0)), 0.1,
                                            key="ni_pd", label_visibility="collapsed")
    else:
        st.caption("Filter OFF — any breakout above/below counts")

    st.markdown("---")

    # ── Indicators ────────────────────────────────────────────
    st.markdown("#### 📈 Indicators")
    cfg["use_rsi"] = st.checkbox("✅ Enable RSI",
                                 value=cfg.get("use_rsi", True), key="cb_rsi")
    if cfg["use_rsi"]:
        c1, c2 = st.columns([3,1])
        with c1:
            cfg["rsi_len"] = st.slider("RSI Length", 2, 50,
                                       int(cfg.get("rsi_len",14)), key="sl_rsi")
        with c2:
            cfg["rsi_len"] = st.number_input("", 2, 50,
                                             int(cfg.get("rsi_len",14)),
                                             key="ni_rsi", label_visibility="collapsed")
    cfg["use_vwap"] = st.checkbox("✅ Enable VWAP",
                                  value=cfg.get("use_vwap", True), key="cb_vwap")

    st.markdown("---")

    # ── Stock Universe ─────────────────────────────────────────
    st.markdown("#### 🗂 Stock Universe")
    preset = st.selectbox("Preset", list(PRESETS.keys()), key="sc_preset")
    sel    = PRESETS[preset]
    st.caption(f"{len(sel)} stocks selected")

    st.session_state["cfg"] = cfg

# ── Fire notifications for new signals ────────────────────────
new_sigs = BgScanner.pop_new_signals()
notif_on   = st.session_state.get("notif_on",   True)
notif_sound= st.session_state.get("notif_sound", True)
notif_push = st.session_state.get("notif_push",  True)

if new_sigs:
    if "notifications" not in st.session_state:
        st.session_state["notifications"] = []
    for n in new_sigs:
        ticker = n["ticker"].replace(".NS","")
        sig    = n["signal"].strip()
        close  = n.get("close","?")
        is_buy = "BUY" in sig
        if notif_on:
            fire_notification(ticker, sig, close, notif_sound, notif_push)
        st.session_state["notifications"].insert(0, {
            "time":datetime.datetime.now(IST).strftime("%H:%M:%S"),
            "ticker":ticker,"signal":sig,"close":close,"is_buy":is_buy,
        })
    st.session_state["notifications"] = st.session_state["notifications"][:50]

# ── Page header ───────────────────────────────────────────────
st.markdown("""
<div style="background:linear-gradient(135deg,#0D1117,#080815);
     border:1px solid #00E5FF33;border-radius:10px;padding:16px 24px;margin-bottom:16px;">
  <h2 style="color:#00E5FF;margin:0;letter-spacing:2px;">📊 PDH / PDL BREAKOUT SCANNER</h2>
  <p style="color:#666;margin:4px 0 0;">
    Background scan · switch pages freely ·
    🔔 browser popup + beep on every BUY/SELL signal
  </p>
</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# 🔔 NOTIFICATION CONTROL PANEL — always visible, easy to find
# ══════════════════════════════════════════════════════════════
notifs      = st.session_state.get("notifications", [])
notif_on    = st.session_state.get("notif_on",    True)
notif_sound = st.session_state.get("notif_sound", True)
notif_push  = st.session_state.get("notif_push",  True)

# Colour the panel border based on ON/OFF state
panel_border = "#00E67655" if notif_on else "#FF174455"
panel_bg     = "#001a0a"   if notif_on else "#1a0000"
status_badge = (
    '<span style="background:#00E676;color:#000;border-radius:4px;padding:2px 10px;'
    'font-size:.8rem;font-weight:bold;">ON</span>'
    if notif_on else
    '<span style="background:#FF1744;color:#fff;border-radius:4px;padding:2px 10px;'
    'font-size:.8rem;font-weight:bold;">OFF</span>'
)

st.markdown(f"""
<div style="background:{panel_bg};border:2px solid {panel_border};
     border-radius:12px;padding:16px 20px;margin-bottom:16px;">
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">
    <span style="font-size:1.4rem;">🔔</span>
    <span style="color:#fff;font-size:1.1rem;font-weight:bold;letter-spacing:1px;">
      NOTIFICATION SETTINGS
    </span>
    {status_badge}
    <span style="color:#666;font-size:.85rem;margin-left:auto;">
      {len(notifs)} alert(s) received this session
    </span>
  </div>
  <p style="color:#888;font-size:.82rem;margin:0;">
    Use the controls below to enable/disable alerts.
    Click <b>Allow</b> if your browser asks for notification permission.
  </p>
</div>
""", unsafe_allow_html=True)

# Controls row
nc1, nc2, nc3, nc4, nc5 = st.columns([2, 2, 2, 2, 2])

with nc1:
    new_notif_on = st.checkbox(
        "🔔 Notifications ON",
        value=notif_on,
        key="ck_notif_on",
        help="Master switch — turn all alerts ON or OFF"
    )
    if new_notif_on != notif_on:
        st.session_state["notif_on"] = new_notif_on
        st.rerun()

with nc2:
    new_sound = st.checkbox(
        "🔊 Sound (Beep)",
        value=notif_sound,
        disabled=not notif_on,
        key="ck_sound",
        help="Play a beep sound — 880Hz for BUY, 440Hz for SELL"
    )
    st.session_state["notif_sound"] = new_sound

with nc3:
    new_push = st.checkbox(
        "🖥 Browser Popup",
        value=notif_push,
        disabled=not notif_on,
        key="ck_push",
        help="Show OS-level browser notification popup"
    )
    st.session_state["notif_push"] = new_push

with nc4:
    # Request permission button
    if st.button("🔑 Allow Notifications", use_container_width=True,
                 help="Click to ask browser for notification permission"):
        components.html("""
<script>
if("Notification" in window && Notification.permission !== "granted"){
    Notification.requestPermission().then(function(p){
        console.log("Notification permission:", p);
    });
}
</script>""", height=0)
        st.toast("Browser permission requested — click Allow in the popup!", icon="🔔")

with nc5:
    if st.button("🗑 Clear Alert Log", use_container_width=True,
                 help="Clear the list of received alerts below"):
        st.session_state["notifications"] = []
        st.rerun()

# ── Alert log — all received alerts this session ───────────────
if notifs:
    with st.expander(f"📋 Alert Log — {len(notifs)} signal(s) received this session", expanded=True):
        for n in notifs[:30]:
            col    = "#00E5FF" if n["is_buy"] else "#FF6D00"
            bg     = "#001820" if n["is_buy"] else "#1A0800"
            icon   = "🟢" if n["is_buy"] else "🔴"
            st.markdown(
                f"<div style='background:{bg};border-left:4px solid {col};"
                f"border-radius:0 6px 6px 0;padding:8px 14px;margin:4px 0;"
                f"font-family:monospace;display:flex;justify-content:space-between;"
                f"align-items:center;'>"
                f"<span style='color:{col};font-weight:bold;font-size:.95rem;'>"
                f"{icon} {n['ticker']} — {n['signal'].strip()}</span>"
                f"<span style='color:#aaa;font-size:.85rem;'>Rs.{n['close']}</span>"
                f"<span style='color:#555;font-size:.8rem;'>{n['time']} IST</span>"
                f"</div>",
                unsafe_allow_html=True
            )
        if len(notifs) > 30:
            st.caption(f"Showing 30 of {len(notifs)}. Clear log to reset.")

st.markdown("---")

# ── Control buttons ───────────────────────────────────────────
b1,b2,b3,b4 = st.columns([1,1,1,3])
with b1:
    if st.button("🚀 Start Scan", use_container_width=True):
        BgScanner.start(cfg, sel); st.rerun()
with b2:
    if st.button("⏹ Stop", use_container_width=True):
        BgScanner.stop(); st.rerun()
with b3:
    if st.button("🔄 Refresh", use_container_width=True): st.rerun()
with b4:
    s = BgScanner.state()
    if s["running"]:
        st.markdown(
            f'<div style="background:#0D1117;border:1px solid #00E5FF33;border-radius:8px;'
            f'padding:9px 16px;font-family:monospace;color:#00E5FF;">'
            f'<span class="pulse"></span>Scanning: <b>{s["current"]}</b> — '
            f'{s["scanned"]}/{s["total"]} — {int(s["progress"]*100)}%</div>',
            unsafe_allow_html=True)
    elif s["done"]:
        t = s["scan_time"].strftime("%H:%M:%S IST") if s["scan_time"] else ""
        st.markdown(
            f'<div style="background:#0D1117;border:1px solid #00E67633;border-radius:8px;'
            f'padding:9px 16px;font-family:monospace;color:#00E676;">'
            f'✅ Complete — {s["scanned"]} stocks — {t}</div>',
            unsafe_allow_html=True)

if BgScanner.is_running():
    time.sleep(1.5); st.rerun()

# Today's history bar
today = get_today()
if today:
    bc = sum(1 for r in today if "BUY"  in r.get("signal",""))
    sc = sum(1 for r in today if "SELL" in r.get("signal",""))
    st.markdown(
        f'<div style="background:#0D1117;border:1px solid #1C1C2E;border-radius:8px;'
        f'padding:8px 16px;margin-bottom:12px;font-size:.85rem;">'
        f'📜 <b>Today\'s saved signals:</b> &nbsp;'
        f'<span style="color:#00E5FF">🟢 {bc} BUY</span> &nbsp;|&nbsp; '
        f'<span style="color:#FF6D00">🔴 {sc} SELL</span></div>',
        unsafe_allow_html=True)

# ── Results ───────────────────────────────────────────────────
results = BgScanner.results()
if not results:
    st.info("👆 Click **Start Scan** — scan runs in background. Switch pages freely.")
    st.markdown("""
**Tips:**
- Use **Nifty 50** preset for a quick ~2 min scan
- Tick/untick checkboxes to enable/disable filters
- Type exact values in the number boxes next to each slider
- Browser will ask for notification permission — click **Allow**
    """)
    st.stop()

buy_l  = [r for r in results if "BUY"  in r["signal"]]
sell_l = [r for r in results if "SELL" in r["signal"]]
nosig  = [r for r in results if "Signal" in r["signal"] and not r.get("error")]
err_l  = [r for r in results if r.get("error")]

st.markdown("---")
m1,m2,m3,m4,m5 = st.columns(5)
m1.metric("Scanned",      len(results))
m2.metric("🟢 BUY",       len(buy_l))
m3.metric("🔴 SELL",      len(sell_l))
m4.metric("⚪ No Signal",  len(nosig))
m5.metric("❌ Errors",    len(err_l))

s = BgScanner.state()
if s.get("scan_time"):
    st.caption(
        f"Scan: {s['scan_time'].strftime('%Y-%m-%d %H:%M:%S IST')} | "
        f"HTF:{s['cfg'].get('htf','?')} | "
        f"Body:{s['cfg'].get('min_body','?')}–{s['cfg'].get('max_body','?')}% | "
        f"Wick≤{s['cfg'].get('max_wick','?')}% | Vol≥{s['cfg'].get('v_mult','?')}x")

st.markdown("---")

def make_row(r):
    is_bull  = r["htf_dir"]=="BULLISH"
    rel_dist = r["pdh_dist_pct"] if is_bull else r["pdl_dist_pct"]
    rsi_v  = f"{r['rsi']:.1f}"  if not math.isnan(r.get("rsi",float("nan")))  else "n/a"
    vwap_v = f"{r['vwap']:.2f}" if not math.isnan(r.get("vwap",float("nan"))) else "n/a"
    sig    = r["signal"].strip()
    return {
        "Ticker"  : r["ticker"].replace(".NS",""),
        "Signal"  : ("🟢 " if "BUY" in sig else "🔴 " if "SELL" in sig else "⚪ ")+sig,
        "Dir"     : ("📈 " if is_bull else "📉 " if r["htf_dir"]=="BEARISH" else "➡ ")+r["htf_dir"][:4],
        "Close Rs": f"{r['close']:.2f}" if not math.isnan(r.get("close",float("nan"))) else "n/a",
        "PDH Rs"  : f"{r['pdh']:.2f}"  if not math.isnan(r.get("pdh",float("nan")))   else "n/a",
        "PDL Rs"  : f"{r['pdl']:.2f}"  if not math.isnan(r.get("pdl",float("nan")))   else "n/a",
        "Dist%"   : f"{rel_dist:.1f}%",
        "Body%"   : f"{r['body_pct']:.1f}%",
        "Wick%"   : f"{r['wick_pct']:.1f}%",
        "VolRatio": f"{r['vol_ratio']:.2f}x",
        "RSI"     : rsi_v,
        "VWAP Rs" : vwap_v,
        "Error"   : r.get("error") or "",
    }

if buy_l or sell_l:
    st.markdown("### 🎯 Active Signals")
    rows = [make_row(r) for r in buy_l+sell_l]
    df   = pd.DataFrame(rows)
    def hl(row):
        if "BUY"  in str(row["Signal"]): return ["color:#00E5FF;font-weight:bold"]*len(row)
        if "SELL" in str(row["Signal"]): return ["color:#FF6D00;font-weight:bold"]*len(row)
        return [""]*len(row)
    st.dataframe(df.style.apply(hl,axis=1), use_container_width=True,
                 hide_index=True, height=min(420,40+35*len(rows)))

st.markdown("### 📋 Full Results")
tabs = st.tabs([f"All({len(results)})",f"🟢BUY({len(buy_l)})",
                f"🔴SELL({len(sell_l)})",f"❌Err({len(err_l)})"])
for tab, lst in zip(tabs,[results,buy_l,sell_l,err_l]):
    with tab:
        if lst: st.dataframe(pd.DataFrame([make_row(r) for r in lst]),
                             use_container_width=True, hide_index=True)
        else:   st.info("None")

st.markdown("---")
df_all = pd.DataFrame([make_row(r) for r in results])
csv = df_all.to_csv(index=False).encode()
st.download_button("⬇️ Download CSV", csv,
                   f"karma_{datetime.datetime.now(IST).strftime('%Y%m%d_%H%M')}.csv","text/csv")
