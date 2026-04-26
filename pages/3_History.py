"""
pages/3_History.py
Merged History — Signal alerts + Full stock snapshots in one place
"""

import streamlit as st, sys, os, math, datetime, pytz, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import plotly.graph_objects as go

from utils.history       import get_all, get_today, clear_all as clear_signals, stats
from utils.stock_history import (
    get_latest_snapshot, get_all_snapshots,
    get_snapshots_for_ticker, get_scan_ids,
    clear_all as clear_snapshots, summary_stats
)
from utils.stocks     import STOCKS
from utils.bg_scanner import BgScanner

IST = pytz.timezone("Asia/Kolkata")
st.set_page_config(page_title="KARMA History", page_icon="📜", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Exo+2:wght@700&display=swap');
html,[class*="css"]{font-family:'Share Tech Mono',monospace;}
h1,h2,h3{font-family:'Exo 2',sans-serif!important;font-weight:700!important;}
[data-testid="metric-container"]{background:#0D1117;border:1px solid #1C1C2E;border-radius:8px;padding:12px;}
.stButton>button{background:linear-gradient(135deg,#00E5FF11,#00E5FF33);
  border:1px solid #00E5FF55;color:#00E5FF;font-family:'Share Tech Mono',monospace;border-radius:6px;}
</style>""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────
with st.sidebar:
    # Background scan — top
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
        st.info("No scan running")
    st.divider()

    st.markdown("### 🔍 Filters")

    # Section toggle
    section = st.radio("View", [
        "📶 Signal Alerts (BUY/SELL only)",
        "🗃️ Full Scan Snapshots (all stocks)"
    ])

    # Common filters
    all_tickers = sorted(set(
        r.get("ticker","").replace(".NS","")
        for r in get_all_snapshots() if r.get("ticker")
    ))
    if not all_tickers:
        all_tickers = sorted(s.replace(".NS","") for s in STOCKS)

    fticker = st.selectbox("Filter by Stock", ["All"] + all_tickers)
    fdate   = st.radio("Date Range", ["Today", "All Time", "Custom"])
    fdate_val = None
    if fdate == "Custom":
        fdate_val = st.date_input("Pick Date", datetime.date.today())
    fsig = st.radio("Signal Type", ["All", "BUY", "SELL", "No Signal"])

    # Snapshot-specific
    if "Snapshots" in section:
        snap_mode = st.radio("Snapshot View", [
            "Latest Scan (all stocks)",
            "By Stock (timeline)",
            "All Records"
        ])
        scan_ids  = get_scan_ids()
        scan_opts = ["All"] + [f"{s['date']} {s['time']} ({s['htf']})" for s in scan_ids]
        sel_scan  = st.selectbox("Scan Run", scan_opts)
    else:
        snap_mode = None
        sel_scan  = "All"
        scan_ids  = []

    st.divider()
    if st.button("🗑 Clear Signal Alerts", use_container_width=True):
        clear_signals(); st.success("Signal alerts cleared."); st.rerun()
    if st.button("🗑 Clear Scan Snapshots", use_container_width=True):
        clear_snapshots(); st.success("Scan snapshots cleared."); st.rerun()

# ── Page header ────────────────────────────────────────────────
st.markdown("""
<div style="background:linear-gradient(135deg,#0D1117,#080815);
     border:1px solid #00E5FF33;border-radius:10px;padding:16px 24px;margin-bottom:16px;">
  <h2 style="color:#00E5FF;margin:0;letter-spacing:2px;">📜 HISTORY</h2>
  <p style="color:#666;margin:4px 0 0;">
    Signal Alerts (BUY/SELL only) · Full Scan Snapshots (all 206 stocks) · all in one place
  </p>
</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# SECTION A — Signal Alerts
# ══════════════════════════════════════════════════════════════
if "Signal" in section:
    st_ = stats()
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Total Signals",   st_["total"])
    c2.metric("🟢 BUY",          st_["buy"])
    c3.metric("🔴 SELL",         st_["sell"])
    c4.metric("Trading Days",    st_["days"])
    c5.metric("Unique Stocks",   st_["tickers"])

    # Load + filter
    all_recs = get_all()
    if fdate == "Today":
        recs = get_today()
    elif fdate == "Custom" and fdate_val:
        ds   = fdate_val.strftime("%Y-%m-%d")
        recs = [r for r in all_recs if r.get("date") == ds]
    else:
        recs = all_recs

    if fticker != "All":
        recs = [r for r in recs if r.get("ticker","").replace(".NS","") == fticker]
    if fsig == "BUY":
        recs = [r for r in recs if "BUY"  in r.get("signal","")]
    elif fsig == "SELL":
        recs = [r for r in recs if "SELL" in r.get("signal","")]
    elif fsig == "No Signal":
        recs = [r for r in recs if "BUY" not in r.get("signal","") and "SELL" not in r.get("signal","")]

    st.caption(f"Showing **{len(recs)}** signal alert(s)")

    if not recs:
        st.info("No signal alerts yet. Run a scan — BUY/SELL signals are saved automatically.")
        st.stop()

    # Build df
    rows = []
    for r in recs:
        ib = "BUY" in r.get("signal","")
        rows.append({
            "Date"     : r.get("date",""),
            "Time"     : r.get("time",""),
            "Ticker"   : r.get("ticker","").replace(".NS",""),
            "Signal"   : ("🟢 " if ib else "🔴 ")+r.get("signal","").strip(),
            "Direction": r.get("direction",""),
            "Close ₹"  : r.get("close",""),
            "PDH ₹"    : r.get("pdh",""),
            "PDL ₹"    : r.get("pdl",""),
            "Dist%"    : f"{r.get('pdh_dist',0):.1f}%",
            "Body%"    : f"{r.get('body_pct',0):.1f}%",
            "Wick%"    : f"{r.get('wick_pct',0):.1f}%",
            "VolRatio" : f"{r.get('vol_ratio',0):.2f}x",
            "RSI"      : r.get("rsi","") or "n/a",
            "VWAP ₹"   : r.get("vwap","") or "n/a",
            "HTF"      : r.get("htf",""),
        })
    df = pd.DataFrame(rows)

    tab_tbl, tab_cards, tab_chart = st.tabs(["📋 Table", "🃏 Cards", "📈 Chart"])

    with tab_tbl:
        def hl_sig(row):
            if "BUY"  in str(row["Signal"]): return ["color:#00E5FF"]+[""]*( len(row)-1)
            if "SELL" in str(row["Signal"]): return ["color:#FF6D00"]+[""]*( len(row)-1)
            return [""]*len(row)
        st.dataframe(df.style.apply(hl_sig, axis=1),
                     use_container_width=True, hide_index=True,
                     height=min(600, 50+35*len(df)))
        csv = df.to_csv(index=False).encode()
        st.download_button("⬇️ Download CSV", csv,
            f"signal_alerts_{datetime.datetime.now(IST).strftime('%Y%m%d_%H%M')}.csv","text/csv")

    with tab_cards:
        for r in recs[:30]:
            ib  = "BUY" in r.get("signal","")
            col = "#00E5FF" if ib else "#FF6D00"
            bg  = "#001820" if ib else "#1A0A00"
            st.markdown(
                f"<div style='border-left:4px solid {col};background:{bg};"
                f"padding:8px 14px;margin:4px 0;border-radius:0 6px 6px 0;'>"
                f"<span style='color:{col};font-weight:bold;font-size:1rem;'>"
                f"{'🟢' if ib else '🔴'} {r.get('ticker','').replace('.NS','')} — {r.get('signal','').strip()}"
                f"</span><span style='color:#888;font-size:.8rem;float:right;'>"
                f"{r.get('date','')} {r.get('time','')} IST | HTF:{r.get('htf','')}</span><br>"
                f"<span style='color:#ccc;font-size:.85rem;'>"
                f"₹{r.get('close','?')} | PDH:₹{r.get('pdh','?')} | PDL:₹{r.get('pdl','?')} | "
                f"Body:{r.get('body_pct',0):.1f}% | Wick:{r.get('wick_pct',0):.1f}% | "
                f"Vol:{r.get('vol_ratio',0):.2f}x | RSI:{r.get('rsi','n/a')}</span></div>",
                unsafe_allow_html=True)
        if len(recs) > 30:
            st.caption(f"Showing 30 of {len(recs)}. Download CSV for all.")

    with tab_chart:
        if len(df) >= 2:
            df2 = df.copy()
            df2["IsBuy"] = df2["Signal"].str.contains("BUY")
            daily = df2.groupby(["Date","IsBuy"]).size().reset_index(name="Count")
            daily["Type"] = daily["IsBuy"].map({True:"BUY",False:"SELL"})
            fig = go.Figure()
            for typ, col in [("BUY","#00E5FF"),("SELL","#FF6D00")]:
                d = daily[daily["Type"]==typ]
                fig.add_trace(go.Bar(x=d["Date"],y=d["Count"],name=typ,marker_color=col))
            fig.update_layout(title="BUY/SELL Signals Per Day",template="plotly_dark",
                              paper_bgcolor="#070710",plot_bgcolor="#0A0A0F",
                              barmode="group",height=350,margin=dict(l=0,r=0,t=40,b=0),
                              font=dict(family="Share Tech Mono,monospace",color="#888"),
                              legend=dict(orientation="h"))
            fig.update_xaxes(gridcolor="#1C1C2E"); fig.update_yaxes(gridcolor="#1C1C2E")
            st.plotly_chart(fig, use_container_width=True)

            top = df2.groupby("Ticker").size().sort_values(ascending=False).head(20)
            fig2 = go.Figure(go.Bar(x=top.index,y=top.values,
                                    marker_color="#00E5FF",opacity=.8))
            fig2.update_layout(title="Top 20 Most Active Signal Stocks",template="plotly_dark",
                               paper_bgcolor="#070710",plot_bgcolor="#0A0A0F",
                               height=300,margin=dict(l=0,r=0,t=40,b=0),
                               font=dict(family="Share Tech Mono,monospace",color="#888"))
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Need at least 2 records for charts.")

# ══════════════════════════════════════════════════════════════
# SECTION B — Full Scan Snapshots
# ══════════════════════════════════════════════════════════════
else:
    snap_stats = summary_stats()
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Total Records",   snap_stats["total_records"])
    c2.metric("Unique Scans",    snap_stats["unique_scans"])
    c3.metric("Unique Stocks",   snap_stats["unique_tickers"])
    c4.metric("Total BUY hits",  snap_stats["total_buy"])
    c5.metric("Total SELL hits", snap_stats["total_sell"])

    if snap_stats["total_records"] == 0:
        st.info("No snapshot history yet. Run a scan — all 206 stocks are saved automatically after each scan.")
        st.stop()

    # Load based on view mode
    if snap_mode == "Latest Scan (all stocks)":
        recs = get_latest_snapshot()
        st.markdown(f"**Latest scan — {len(recs)} stocks**")
    elif snap_mode == "By Stock (timeline)":
        recs = get_snapshots_for_ticker((fticker+".NS") if fticker != "All" else ".NS")
        st.markdown(f"**Timeline for {fticker}**")
    else:
        recs = get_all_snapshots()

    # Apply scan filter
    if sel_scan != "All" and scan_ids:
        idx = scan_opts.index(sel_scan) - 1
        if 0 <= idx < len(scan_ids):
            sid  = scan_ids[idx]["scan_id"]
            recs = [r for r in recs if r.get("scan_id") == sid]

    # Apply ticker filter
    if fticker != "All":
        recs = [r for r in recs if r.get("ticker","").replace(".NS","") == fticker]

    # Apply signal filter
    if fsig == "BUY":
        recs = [r for r in recs if "BUY"  in r.get("signal","")]
    elif fsig == "SELL":
        recs = [r for r in recs if "SELL" in r.get("signal","")]
    elif fsig == "No Signal":
        recs = [r for r in recs if "BUY" not in r.get("signal","") and
                                   "SELL" not in r.get("signal","")]

    # Apply date filter
    if fdate == "Today":
        today_str = datetime.datetime.now(IST).strftime("%Y-%m-%d")
        recs = [r for r in recs if r.get("date","") == today_str]
    elif fdate == "Custom" and fdate_val:
        ds   = fdate_val.strftime("%Y-%m-%d")
        recs = [r for r in recs if r.get("date","") == ds]

    st.caption(f"Showing **{len(recs)}** records")

    if not recs:
        st.info("No records match current filters.")
        st.stop()

    # Build df
    rows = []
    for r in recs:
        sig    = r.get("signal","").strip()
        is_buy = "BUY"  in sig
        is_sell= "SELL" in sig
        rows.append({
            "Date"     : r.get("date",""),
            "Time"     : r.get("time",""),
            "HTF"      : r.get("htf",""),
            "Ticker"   : r.get("ticker","").replace(".NS",""),
            "Signal"   : ("🟢 " if is_buy else "🔴 " if is_sell else "⚪ ")+sig,
            "Direction": r.get("direction",""),
            "Close ₹"  : r.get("close",""),
            "PDH ₹"    : r.get("pdh",""),
            "PDL ₹"    : r.get("pdl",""),
            "Dist%"    : f"{r.get('dist_pct',0):.1f}%" if r.get("dist_pct") is not None else "n/a",
            "Body%"    : f"{r.get('body_pct',0):.1f}%" if r.get("body_pct") is not None else "n/a",
            "Wick%"    : f"{r.get('wick_pct',0):.1f}%" if r.get("wick_pct") is not None else "n/a",
            "VolRatio" : f"{r.get('vol_ratio',0):.2f}x" if r.get("vol_ratio") is not None else "n/a",
            "BodyOK"   : "✅" if r.get("body_ok") else "❌",
            "WickOK"   : "✅" if r.get("wick_ok") else "❌",
            "VolOK"    : "✅" if r.get("vol_ok")  else "❌",
            "RSI"      : f"{r.get('rsi',0):.1f}" if r.get("rsi") is not None else "n/a",
            "VWAP ₹"   : f"{r.get('vwap',0):.2f}" if r.get("vwap") is not None else "n/a",
        })
    df = pd.DataFrame(rows)

    tab_tbl, tab_chart = st.tabs(["📋 Table", "📈 Charts"])

    with tab_tbl:
        def hl_snap(row):
            if "BUY"  in str(row["Signal"]): return ["color:#00E5FF"]+[""]*( len(row)-1)
            if "SELL" in str(row["Signal"]): return ["color:#FF6D00"]+[""]*( len(row)-1)
            return [""]*len(row)
        st.dataframe(df.style.apply(hl_snap, axis=1),
                     use_container_width=True, hide_index=True,
                     height=min(700, 50+35*len(df)))
        csv = df.to_csv(index=False).encode()
        st.download_button("⬇️ Download CSV", csv,
            f"scan_snapshot_{datetime.datetime.now(IST).strftime('%Y%m%d_%H%M')}.csv","text/csv")

    with tab_chart:
        if len(recs) >= 2:
            col_a, col_b = st.columns(2)
            with col_a:
                sig_counts = {"BUY":0,"SELL":0,"No Signal":0}
                for r in recs:
                    s2 = r.get("signal","")
                    if "BUY"  in s2: sig_counts["BUY"]  += 1
                    elif "SELL" in s2: sig_counts["SELL"] += 1
                    else: sig_counts["No Signal"] += 1
                fig = go.Figure(go.Pie(
                    labels=list(sig_counts.keys()),
                    values=list(sig_counts.values()),
                    marker=dict(colors=["#00E5FF","#FF6D00","#333333"]),
                    hole=0.4))
                fig.update_layout(title="Signal Distribution",template="plotly_dark",
                                  paper_bgcolor="#070710",height=300,
                                  margin=dict(l=0,r=0,t=40,b=0),
                                  font=dict(family="Share Tech Mono,monospace",color="#888"))
                st.plotly_chart(fig, use_container_width=True)
            with col_b:
                fn = ["Body","Wick","Vol","PDH","PDL"]
                fk = ["body_ok","wick_ok","vol_ok","pdh_ok","pdl_ok"]
                pr = [round(sum(1 for r in recs if r.get(k))/max(len(recs),1)*100,1) for k in fk]
                fig2 = go.Figure(go.Bar(x=fn,y=pr,marker_color="#00E676",opacity=.8))
                fig2.update_layout(title="Filter Pass Rate (%)",template="plotly_dark",
                                   paper_bgcolor="#070710",height=300,
                                   margin=dict(l=0,r=0,t=40,b=0),
                                   yaxis=dict(range=[0,100]),
                                   font=dict(family="Share Tech Mono,monospace",color="#888"))
                st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Need more records for charts.")

st.caption(f"Data saved in signal_history.json & stock_history.json | {datetime.datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST')}")
