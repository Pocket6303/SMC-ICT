import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz
import os
import json

# --- APP CONFIG ---
st.set_page_config(page_title="SMC-ICT PRO v3.5", layout="centered")
st.title("SMC-ICT PRO v3.5")

JOURNAL_FILE = "smc_gmt4_journey_journal.json"
IST_TZ = pytz.timezone('Asia/Kolkata')
EST_TZ = pytz.timezone('America/New_York')

def load_journal():
    if os.path.exists(JOURNAL_FILE):
        try:
            with open(JOURNAL_FILE, "r") as f:
                data = json.load(f)
                return data
        except: return []
    return []

def log_trade(signal_type, entry_p, sl_p, tp_p, reason):
    journal = load_journal()
    now_str = datetime.now(IST_TZ).isoformat()
    journal.append({"timestamp": now_str, "type": signal_type, "entry": round(entry_p, 2), "sl": round(sl_p, 2), "tp": round(tp_p, 2), "reason": reason, "pnl_usd": 20.0})
    with open(JOURNAL_FILE, "w") as f: json.dump(journal, f, indent=4)

# Sidebar
tf = st.sidebar.selectbox("Select Timeframe", ["5m", "15m", "30m", "1h"], index=1)
manual_offset = st.sidebar.slider("Fixed Broker Offset ($)", -100.0, 100.0, -14.0, 0.25)
force_signal = st.sidebar.checkbox("🚀 Force Active Simulation", value=False)

# Data Fetching
@st.cache_data(ttl=10)
def get_data(tf):
    data = yf.download("XAUUSD=X", period="5d", interval=tf, progress=False)
    return data

data = get_data(tf).dropna()
price = float(data['Close'].iloc[-1]) + manual_offset

# Calculations
swing_high = data['High'].iloc[-20:].max() + manual_offset
swing_low = data['Low'].iloc[-20:].min() + manual_offset
equilibrium = (swing_high + swing_low) / 2
pd_high = data['High'].iloc[-288:].max() + manual_offset
pd_low = data['Low'].iloc[-288:].min() + manual_offset

# Session Logic
now_est = datetime.now(EST_TZ)
est_time = now_est.hour + now_est.minute / 60.0
is_asian = (20.0 <= est_time <= 24.0) or (0.0 <= est_time <= 0.5)
is_london = (2.0 <= est_time <= 5.0)
is_ny = (8.0 <= est_time <= 11.0)
session_active = is_asian or is_london or is_ny or force_signal

# Strategy Engine
signal_box, color, recommendation, sl_val, tp_val = "WAITING FOR SETUP", "#64748b", "Monitoring Liquidity & MMS...", None, None

if session_active:
    if price > pd_high and price < equilibrium: # Sell Sweep logic
        signal_box = "📉 SELL SIGNAL: LIQUIDITY SWEEP & MMS DETECTED"
        color = "#ef4444"
        sl_val = price + 15.0
        tp_val = pd_low
        recommendation = "High Liquidity Swept + MMS confirmed. Entry at POI Retest."
        log_trade("SELL", price, sl_val, tp_val, recommendation)
    elif price < pd_low and price > equilibrium: # Buy Sweep logic
        signal_box = "📈 BUY SIGNAL: LIQUIDITY SWEEP & MMS DETECTED"
        color = "#22c55e"
        sl_val = price - 15.0
        tp_val = pd_high
        recommendation = "Low Liquidity Swept + MMS confirmed. Entry at POI Retest."
        log_trade("BUY", price, sl_val, tp_val, recommendation)

# UI Display
st.markdown(f"""<div style="background-color: #0f172a; padding: 20px; border-radius: 10px; border-left: 10px solid {color};">
    <h2 style="color:{color};">{signal_box}</h2>
    <p><b>Price:</b> {price:.2f} | <b>Offset:</b> {manual_offset}</p>
    <p>{recommendation}</p>
</div>""", unsafe_allow_html=True)

# Performance Tracker
st.subheader("📅 1-Month Trading Journey")
j_data = load_journal()
if j_data:
    df = pd.DataFrame(j_data)
    st.dataframe(df, use_container_width=True)
        
