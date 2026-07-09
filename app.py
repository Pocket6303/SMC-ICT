import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz
import os
import json

# --- APP CONFIG ---
st.set_page_config(page_title="XAUUSD Master Institutional Engine v5.46.2", layout="centered")

st.title("🏛️ XAUUSD Master Institutional Engine v5.46.2")

JOURNAL_FILE = "smc_gmt4_journey_journal.json"
IST_TZ = pytz.timezone('Asia/Kolkata')

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

# --- SIDEBAR ---
tf = st.sidebar.selectbox("Select Timeframe", ["5m", "15m", "1h", "4h"], index=3)
manual_offset = st.sidebar.slider("Fixed Broker Offset ($)", -200.0, 200.0, -35.0, 0.25)
force_active = st.sidebar.checkbox("🚀 Force Active Confluence Trigger", value=False)

# Data Fetching
@st.cache_data(ttl=5)
def get_data(ticker, interval):
    df = yf.download(ticker, period="60d", interval=interval, progress=False)
    if df.empty: df = yf.download("GC=F", period="60d", interval=interval, progress=False)
    return df

raw_df = get_data("XAUUSD=X", tf)
if raw_df.empty or len(raw_df) < 210:
    raw_df = get_data("XAUUSD=X", "1h")
    if raw_df.empty or len(raw_df) < 210:
        st.error("Data syncing failed.")
        st.stop()

if isinstance(raw_df.columns, pd.MultiIndex): 
    raw_df.columns = raw_df.columns.get_level_values(0)

data = raw_df.dropna()
price = float(data['Close'].iloc[-1]) + manual_offset
atr_val = float((data['High'] - data['Low']).iloc[-10:].mean())

# EMA & SMC
data['EMA_20'] = data['Close'].ewm(span=20, adjust=False).mean()
data['EMA_200'] = data['Close'].ewm(span=200, adjust=False).mean()
ema20_val = float(data['EMA_20'].iloc[-1]) + manual_offset
ema200_val = float(data['EMA_200'].iloc[-1]) + manual_offset
recent_max = float(data['High'].iloc[-5:-1].max()) + manual_offset
recent_min = float(data['Low'].iloc[-5:-1].min()) + manual_offset

# Logic
distance_from_ema20 = abs(price - ema20_val)
ema_tap_valid = distance_from_ema20 <= (atr_val * 0.8)
trade_type = "NONE"

# --- NATIVE UI COMPONENTS (NO HTML STRING) ---
st.info("⏳ Monitoring SMC/ICT + EMA Confluence...")

if force_active or (ema_tap_valid and price > recent_max and price > ema200_val):
    st.success("🚨 ALARM: SMC BUY SWEEP + 20 EMA BOUNCE")
    trade_type = "BUY"
    sl, tp = price - (atr_val * 0.8), price + (atr_val * 3.2)
elif force_active or (ema_tap_valid and price < recent_min and price < ema200_val):
    st.error("🚨 ALARM: SMC SELL SWEEP + 20 EMA REJECTION")
    trade_type = "SELL"
    sl, tp = price + (atr_val * 0.8), price - (atr_val * 3.2)

# Metrics Display
col1, col2 = st.columns(2)
with col1:
    st.metric("Price (w/ Offset)", f"{price:.2f}")
    st.metric("20 EMA (Green)", f"{ema20_val:.2f}")
with col2:
    st.metric("ATR Volatility", f"{atr_val:.2f}")
    st.metric("200 EMA (Red)", f"{ema200_val:.2f}")

if trade_type != "NONE":
    st.warning(f"**Stop Loss:** {sl:.2f} | **Take Profit (1:4):** {tp:.2f}")
    st.balloons()

# --- JOURNAL ---
st.markdown("---")
st.subheader("📅 30-Day Scalping Journal")
j_data = load_journal()
if j_data:
    st.dataframe(pd.DataFrame(j_data), use_container_width=True)
else:
    st.write("No signals recorded yet.")
    
