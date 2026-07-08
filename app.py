import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz
import os
import json

# --- APP CONFIG ---
st.set_page_config(page_title="SMC-ICT PRO v6.0", layout="centered")
st.title("SMC-ICT PRO v6.0")

JOURNAL_FILE = "smc_gmt4_journey_journal.json"
EST_TZ = pytz.timezone('America/New_York')

def load_journal():
    if os.path.exists(JOURNAL_FILE):
        try:
            with open(JOURNAL_FILE, "r") as f: return json.load(f)
        except: return []
    return []

def log_trade(signal_type, entry_p, sl_p, tp_p, reason):
    journal = load_journal()
    now_str = datetime.now(EST_TZ).isoformat()
    # Check for duplicates to prevent log flooding
    if not journal or (datetime.now(EST_TZ) - datetime.fromisoformat(journal[-1]['timestamp'])).seconds > 1800:
        journal.append({"timestamp": now_str, "type": signal_type, "entry": round(entry_p, 2), "sl": round(sl_p, 2), "tp": round(tp_p, 2), "reason": reason})
        with open(JOURNAL_FILE, "w") as f: json.dump(journal, f, indent=4)

# Sidebar
tf = st.sidebar.selectbox("Select Timeframe", ["5m", "15m", "30m", "1h"], index=1)
manual_offset = st.sidebar.slider("Fixed Broker Offset ($)", -100.0, 100.0, -14.0, 0.25)
force_signal = st.sidebar.checkbox("🚀 Force Active Simulation", value=False)

# Data Fetching
@st.cache_data(ttl=10)
def get_data(tf):
    df = yf.download("XAUUSD=X", period="5d", interval=tf, progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    return df

data = get_data(tf).dropna()
price = float(data['Close'].iloc[-1]) + manual_offset
# Reference levels
pd_high, pd_low = data['High'].iloc[-288:].max() + manual_offset, data['Low'].iloc[-288:].min() + manual_offset
sess_high, sess_low = data['High'].iloc[-20:].max() + manual_offset, data['Low'].iloc[-20:].min() + manual_offset

# Session Logic
now_est = datetime.now(EST_TZ)
est_hour = now_est.hour + now_est.minute / 60.0
is_active = (20.0 <= est_hour <= 24.0) or (0.0 <= est_hour <= 0.5) or (2.0 <= est_hour <= 5.0) or (8.0 <= est_hour <= 11.0) or force_signal

# Strategy Engine
signal_box, color, rec = "WAITING FOR LIQUIDITY SWEEP", "#64748b", "Monitoring PDH/PDL and Session High/Low..."
if is_active:
    # Liquidity Sweep Logic
    if price > pd_high or price > sess_high:
        signal_box, color, rec = "📉 SELL SIGNAL: LIQUIDITY SWEEP", "#ef4444", "Sweep detected at High. Awaiting MSS + POI Retest."
        log_trade("SELL", price, price+15, sess_low, rec)
    elif price < pd_low or price < sess_low:
        signal_box, color, rec = "📈 BUY SIGNAL: LIQUIDITY SWEEP", "#22c55e", "Sweep detected at Low. Awaiting MSS + POI Retest."
        log_trade("BUY", price, price-15, sess_high, rec)

# UI Display
st.markdown(f"""<div style="background-color: #0f172a; padding: 20px; border-radius: 10px; border-left: 10px solid {color};">
    <h2 style="color:{color};">{signal_box}</h2>
    <p><b>Price:</b> {price:.2f} | <b>Offset:</b> {manual_offset}</p>
    <p>{rec}</p>
</div>""", unsafe_allow_html=True)

# Missed Trade Box (New Feature)
st.subheader("🎯 Last Triggered Setup (Missed Trade Log)")
j_data = load_journal()
if j_data:
    last = j_data[-1]
    st.info(f"Last Entry: {last['entry']} | Target: {last['tp']} | Reason: {last['reason']}")

# Performance Tracker
st.subheader("📅 Trading History")
if j_data: st.dataframe(pd.DataFrame(j_data), use_container_width=True)
    
