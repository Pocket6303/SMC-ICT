import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz
import os
import json

# --- APP CONFIG ---
st.set_page_config(page_title="SMC-ICT PRO v4.1", layout="centered")
st.title("SMC-ICT PRO v4.1")

# --- DATA FETCHING (FIXED) ---
@st.cache_data(ttl=10)
def get_data(tf):
    df = yf.download("XAUUSD=X", period="5d", interval=tf, progress=False)
    if df.empty or 'Close' not in df.columns:
        df = yf.download("GC=F", period="5d", interval=tf, progress=False)
    
    # Fix for MultiIndex columns
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

# Sidebar
tf = st.sidebar.selectbox("Select Timeframe", ["5m", "15m", "30m", "1h"], index=1)
manual_offset = st.sidebar.slider("Fixed Broker Offset ($)", -100.0, 100.0, -14.0, 0.25)
force_signal = st.sidebar.checkbox("🚀 Force Active Simulation", value=False)

data = get_data(tf).dropna()
if data.empty or len(data) < 20:
    st.warning("⚠️ Syncing data... please wait.")
    st.stop()

# Calculations
price = float(data['Close'].iloc[-1]) + manual_offset
pd_high = data['High'].iloc[-288:].max() + manual_offset
pd_low = data['Low'].iloc[-288:].min() + manual_offset

# Session Logic (EST)
now_est = datetime.now(pytz.timezone('America/New_York'))
est_hour = now_est.hour + now_est.minute / 60.0
session_active = (20.0 <= est_hour <= 24.0) or (0.0 <= est_hour <= 0.5) or (2.0 <= est_hour <= 5.0) or (8.0 <= est_hour <= 11.0) or force_signal

# Engine
signal_box, color = "WAITING FOR LIQUIDITY SWEEP", "#64748b"
if session_active:
    if price > pd_high:
        signal_box, color = "📉 SELL SIGNAL: SWEEP DETECTED", "#ef4444"
    elif price < pd_low:
        signal_box, color = "📈 BUY SIGNAL: SWEEP DETECTED", "#22c55e"

# UI Display
st.markdown(f"""<div style="background-color: #0f172a; padding: 20px; border-radius: 10px; border-left: 10px solid {color};">
    <h2 style="color:{color};">{signal_box}</h2>
    <p><b>Current Price:</b> {price:.2f}</p>
</div>""", unsafe_allow_html=True)
