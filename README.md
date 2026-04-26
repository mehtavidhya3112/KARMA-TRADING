# 🔥 KARMA Price Action — PDH/PDL Breakout Scanner

A **Streamlit web app** that converts the KARMA PRICE ACTION Pine Script indicator into a live multi-stock NSE scanner with background scanning, browser alerts, signal history, and full filter controls.

---

## 📁 Project Structure

```
karma_app/
│
├── app.py                    ← Main entry point (run this)
├── run.bat                   ← Windows one-click launcher
├── requirements.txt          ← All Python dependencies
├── README.md                 ← This file
│
├── .streamlit/
│   └── config.toml           ← Dark trading terminal theme
│
├── pages/
│   ├── 1_Scanner.py          ← Multi-stock background scanner
│   ├── 2_Dashboard.py        ← Single stock deep-dive
│   ├── 3_History.py          ← Past signal history
│   └── 4_Settings.py         ← All filter inputs
│
└── utils/
    ├── scanner.py            ← Core Pine Script logic (exact mirror)
    ├── bg_scanner.py         ← Background thread engine
    ├── indicators.py         ← RSI, VWAP, SMA calculations
    ├── history.py            ← Signal history (saves to JSON)
    └── stocks.py             ← 206 NSE stocks + presets
```

---

## 🚀 Quick Start (VS Code)

### Step 1 — Open folder in VS Code
```
File → Open Folder → select karma_app folder
```

### Step 2 — Open terminal in VS Code
```
Ctrl + `  (backtick)
```

### Step 3 — Install dependencies
```powershell
pip install -r requirements.txt
```

### Step 4 — Run the app
```powershell
python -m streamlit run app.py
```

App opens at **http://localhost:8501**

---

## 🖱️ One-Click Launch (Windows)

Double-click **`run.bat`** — it installs requirements and launches the app automatically.

---

## 📊 Pages

| Page | Description |
|------|-------------|
| 🏠 **Home** | Overview, scan status banner |
| 📊 **Scanner** | Scan all 206 stocks in background thread |
| 🔍 **Dashboard** | Single stock: Pine Script table + chart + history |
| 📜 **History** | All past BUY/SELL alerts with filters + charts |
| ⚙️ **Settings** | All Pine Script inputs with checkboxes + sliders + number inputs |

---

## 🔔 Notifications

When a BUY or SELL signal fires:
1. **Streamlit toast** — top-right popup (always works)
2. **Browser push notification** — OS-level popup (click Allow when prompted)
3. **Audio beep** — 880Hz for BUY, 440Hz for SELL

---

## 📐 Signal Logic (Exact Pine Script Mirror)

### BUY — PDH Breakout
- HTF candle is **Bullish** (close > open)
- Body % between `min_body` and `max_body`
- Wick % ≤ `max_wick`
- Volume ≥ `v_mult × SMA(volume, v_len)`
- Close ≥ PDH × (1 + `pd_pct` / 100)
- NOT the 9:15 AM IST opening candle

### SELL — PDL Breakdown
- HTF candle is **Bearish** (close < open)
- Body % between `min_body` and `max_body`
- Wick % ≤ `max_wick`
- Volume ≥ `v_mult × SMA(volume, v_len)`
- Close ≤ PDL × (1 − `pd_pct` / 100)
- NOT the 9:15 AM IST opening candle

---

## ⚙️ Default Settings (Pine Script Defaults)

| Parameter | Default | Pine Variable |
|-----------|---------|---------------|
| HTF Timeframe | 15m | `i_htf` |
| Min Body % | 75.0 | `i_minB` |
| Max Body % | 80.0 | `i_maxB` |
| Max Wick % | 20.0 | `i_maxW` |
| Vol MA Length | 20 | `i_vlen` |
| Vol Multiplier | 1.5x | `i_vmult` |
| PDH/PDL % | 1.0% | `i_pdPct` |
| RSI Length | 14 | `i_rsiLen` |

---

## 📦 Dependencies

```
streamlit      — Web UI
yfinance       — NSE live/historical data
pandas         — Data processing
plotly         — Interactive charts
pytz           — IST timezone
colorama       — Terminal colors
tabulate       — Table formatting
numpy          — Numerical operations
requests       — HTTP requests
```

---

## 💡 Tips

- Use **Nifty 50** preset for a quick ~2 minute test scan
- Loosen filters (Body 70–85%, PDH/PDL% 0.5%) to get more signals
- The scan **runs in the background** — switch pages freely while scanning
- Signals are **auto-saved** to `signal_history.json` — persists across restarts
- Use the **number input boxes** next to sliders to type exact values

---

## ⚠️ Notes

- Data source: **Yahoo Finance** (yfinance) — NSE `.NS` tickers
- Market hours: Best results during **9:15 AM – 3:30 PM IST**
- Scanning 206 stocks takes approximately **3–5 minutes**
- Python **3.10 to 3.13** supported (NOT 3.14 — pandas_ta incompatible)
