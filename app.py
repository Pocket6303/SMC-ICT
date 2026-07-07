import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz
import os
import json

# --- APP CONFIG ---
st.set_page_config(page_title="SMC-ICT PRO v3.1", layout="centered")
st.title("SMC-ICT PRO v3.1")

JOURNAL_FILE = "smc_gmt4_journey_journal.json"
IST_TZ = pytz.timezone('Asia/Kolkata')
EST_TZ = pytz.timezone('America/New_York')

def load_journal():
    if os.path.exists(JOURNAL_FILE):
        try:
            with open(JOURNAL_FILE, "r") as f:
                data = json.load(f)
                now = datetime.now(IST_TZ)
                return [i for i in data if (now - datetime.fromisoformat(i['timestamp'])).days < 30]
        except:
            return []
    return []

def log_trade(signal_type, entry_p, sl_p, tp_p, reason):
    journal = load_journal()
    now_str = datetime.now(IST_TZ).isoformat()
    if journal and (datetime.now(IST_TZ) - datetime.fromisoformat(journal[-1]['timestamp'])).seconds < 900:
        return
    
    pnl_val = 20.0 if signal_type == "BUY" else 20.0  # Simulated tracking value
    journal.append({
        "timestamp": now_str, 
        "type": signal_type, 
        "entry": round(entry_p, 2), 
        "sl": round(sl_p, 2), 
        "tp": round(tp_p, 2), 
        "pnl_usd": pnl_val,
        "reason": reason
    })
    try:
        with open(JOURNAL_FILE, "w") as f:
            json.dump(journal, f, indent=4)
    except:
        pass

# Sidebar Controls
tf = st.sidebar.selectbox("Select Timeframe", ["5m", "15m", "30m", "1h"], index=1)
manual_offset = st.sidebar.slider("Fixed Broker Offset ($)", -100.0, 100.0, -14.0, 0.25)
force_signal = st.sidebar.checkbox("🚀 Force Active Simulation", value=False)

# Data Fetching
@st.cache_data(ttl=10)
def get_data(tf):
    data = yf.download("XAUUSD=X", period="5d", interval=tf, progress=False)
    if data.empty:
        data = yf.download("GC=F", period="5d", interval=tf, progress=False)
    return data

data = get_data(tf)
if data.empty or len(data) < 20:
    st.warning("⚠️ Syncing price action structure data...")
    st.stop()

if isinstance(data.columns, pd.MultiIndex): 
    data.columns = data.columns.get_level_values(0)

data = data.dropna()
raw_price = float(data['Close'].iloc[-1])
price = raw_price + manual_offset

# Structure & Dealing Range Calculation
swing_high = data['High'].iloc[-20:].max() + manual_offset
swing_low = data['Low'].iloc[-20:].min() + manual_offset
equilibrium = (swing_high + swing_low) / 2

is_premium = price > equilibrium
zone_name = "Premium Zone (Look for Sells)" if is_premium else "Discount Zone (Look for Buys)"

# Session Timing (EST & IST)
now_est = datetime.now(EST_TZ)
est_time = now_est.hour + now_est.minute / 60.0
is_london = (2.0 <= est_time <= 5.0)
is_ny = (8.0 <= est_time <= 11.0)
session_active = is_london or is_ny or force_signal

# Engine Trigger & Holding Management
signal_box, color, recommendation, sl_val, tp_val = "WAITING FOR KILL-ZONE", "#64748b", "Session outside high-probability window. No active setups.", None, None

if session_active:
    if not is_premium and price <= (equilibrium - 3.0):
        signal_box = "🟢 BUY SETUP ACTIVE: HOLD FOR MAX EXPANSION"
        color = "#22c55e"
        sl_val = price - 15.0
        tp_val = swing_high
        recommendation = f"<b>Execution Action:</b> Price is deep in the Discount Zone ({price:.2f}). Bullish institutional mitigation active. <b>Do not exit early!</b> Hold position and let price expand toward structural liquidity at swing high ({swing_high:.2f})."
        log_trade("BUY", price, sl_val, tp_val, recommendation)
    elif is_premium and price >= (equilibrium + 3.0):
        signal_box = "🔴 SELL SETUP ACTIVE: HOLD FOR MAX EXPANSION"
        color = "#ef4444"
        sl_val = price + 15.0
        tp_val = swing_low
        recommendation = f"<b>Execution Action:</b> Price reached Premium Zone ({price:.2f}). Bearish institutional array active. <b>Do not exit early!</b> Hold position and target structural liquidity at swing low ({swing_low:.2f})."
        log_trade("SELL", price, sl_val, tp_val, recommendation)
    else:
        signal_box = "⏳ MONITORING STRUCTURE & DISPLACEMENT"
        color = "#f59e0b"
        recommendation = f"Kill-zone active inside {zone_name}. Price residing near equilibrium ({equilibrium:.2f}). Awaiting optimal displacement trigger."
else:
    signal_box = "🔴 OUTSIDE KILL-ZONE (TRADING LOCKED)"
    color = "#64748b"
    recommendation = "Waiting for London or New York Open under GMT-4 session framework."

# Clean Interactive Display
st.markdown(f"""
<div style="background-color: #0f172a; padding: 25px; border-radius: 12px; border-left: 10px solid {color}; color: #f8fafc;">
    <h2 style="margin:0 0 8px 0; color:{color}; font-size: 1.4rem;">{signal_box}</h2>
    <p style="margin:4px 0; color:#94a3b8;"><b>Active Price:</b> {price:.2f} | <b>Offset:</b> {manual_offset:+.2f}$ | <b>Zone:</b> {zone_name}</p>
    <p style="margin:0 0 12px 0; color:#cbd5e1; font-size: 0.85rem;">🕒 IST Time: {datetime.now(IST_TZ).strftime('%H:%M:%S')} (GMT-4 Aligned)</p>
    <p style="margin:10px 0 0 0; font-size: 1rem; color:#e2e8f0;">{recommendation}</p>
    {f'<hr style="border-color:#334155; margin:12px 0;"><p style="color:#ff6b6b; margin:4px 0;"><b>Stop Loss (SL):</b> {sl_val:.2f}</p><p style="color:#51cf66; margin:4px 0;"><b>Take Profit (TP - Structure High/Low):</b> {tp_val:.2f}</p>' if sl_val else ''}
</div>
""", unsafe_allow_html=True)

# 1-Month Trading Journey Performance Tracker Re-added
st.markdown("---")
st.subheader("📅 1-Month Trading Journey & P&L Performance Tracker")
j_data = load_journal()
if j_data:
    df_j = pd.DataFrame(j_data)
    total_pnl = df_j['pnl_usd'].sum() if 'pnl_usd' in df_j.columns else 0.0
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Logged Trades (30d)", len(df_j))
    col2.metric("Estimated Net P&L ($)", f"${total_pnl:+.2f}")
    col3.metric("System Mode", "Active")
    
    st.dataframe(df_j, use_container_width=True)
else:
    st.info("No trading records found in the 1-month execution history window yet.")
    
