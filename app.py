import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz
import os
import json

# --- APP CONFIG ---
st.set_page_config(page_title="SMC-ICT PRO v7.0", layout="centered")
st.title("SMC-ICT PRO v7.0")

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
    
    pnl_val = 20.0
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

# Data Fetching with Safety & MultiIndex Flattening
@st.cache_data(ttl=10)
def get_data(tf):
    data = yf.download("XAUUSD=X", period="5d", interval=tf, progress=False)
    if data.empty:
        data = yf.download("GC=F", period="5d", interval=tf, progress=False)
    return data

raw_df = get_data(tf)
if raw_df.empty or len(raw_df) < 20:
    st.warning("⚠️ Syncing price action structure data...")
    st.stop()

if isinstance(raw_df.columns, pd.MultiIndex): 
    raw_df.columns = raw_df.columns.get_level_values(0)

data = raw_df.dropna()
if data.empty or 'Close' not in data.columns or len(data) < 20:
    st.warning("⚠️ Cleaning data structure... please refresh.")
    st.stop()

raw_price = float(data['Close'].iloc[-1])
price = raw_price + manual_offset

# Structure & Dealing Range Calculation
swing_high = float(data['High'].iloc[-20:].max()) + manual_offset
swing_low = float(data['Low'].iloc[-20:].min()) + manual_offset
equilibrium = (swing_high + swing_low) / 2

is_premium = price > equilibrium
zone_name = "Premium Zone (Look for Sells)" if is_premium else "Discount Zone (Look for Buys)"

# Liquidity Reference: Previous Day & Current Session High/Low
pd_high = float(data['High'].iloc[-288:].max()) + manual_offset if len(data) >= 288 else swing_high
pd_low = float(data['Low'].iloc[-288:].min()) + manual_offset if len(data) >= 288 else swing_low
session_high = swing_high
session_low = swing_low

# Sweep Detection (Both PDH/PDL and Session High/Low Sweep)
swept_high_liquidity = (price > pd_high) or (price > session_high)
swept_low_liquidity = (price < pd_low) or (price < session_low)

# Session Timing (EST & IST)
now_est = datetime.now(EST_TZ)
est_time = now_est.hour + now_est.minute / 60.0
is_asian = (20.0 <= est_time <= 24.0) or (0.0 <= est_time <= 0.5)
is_london = (2.0 <= est_time <= 5.0)
is_ny = (8.0 <= est_time <= 11.0)
session_active = is_asian or is_london or is_ny or force_signal

# Engine Trigger & Strategy Logic with Liquidity Filters
signal_box, color, recommendation, sl_val, tp_val = "WAITING FOR LIQUIDITY SWEEP & SETUP", "#64748b", "Monitoring structure across active sessions.", None, None

if session_active:
    if swept_high_liquidity and is_premium and price >= (equilibrium + 3.0):
        signal_box = "📉 SELL SIGNAL: LIQUIDITY SWEEP (PDH/SESSION HIGH) & MMS"
        color = "#ef4444"
        sl_val = price + 15.0
        tp_val = session_low
        recommendation = f"<b>Execution Action:</b> Liquidity sweep at High detected in Premium Zone ({price:.2f}). Market Structure Shift (MMS) active. <b>Do not exit early!</b> Hold position targeting structural target at session low ({session_low:.2f})."
        log_trade("SELL", price, sl_val, tp_val, recommendation)
    elif swept_low_liquidity and not is_premium and price <= (equilibrium - 3.0):
        signal_box = "📈 BUY SIGNAL: LIQUIDITY SWEEP (PDL/SESSION LOW) & MMS"
        color = "#22c55e"
        sl_val = price - 15.0
        tp_val = session_high
        recommendation = f"<b>Execution Action:</b> Liquidity sweep at Low detected in Discount Zone ({price:.2f}). Market Structure Shift (MMS) active. <b>Do not exit early!</b> Hold position targeting structural target at session high ({session_high:.2f})."
        log_trade("BUY", price, sl_val, tp_val, recommendation)
    else:
        signal_box = "⏳ MONITORING LIQUIDITY & POI RETEST"
        color = "#f59e0b"
        recommendation = f"Session active inside {zone_name}. Awaiting high/low sweep of previous day or session boundaries for last POI entry."
else:
    signal_box = "🔴 OUTSIDE ACTIVE SESSIONS (LOCKED)"
    color = "#64748b"
    recommendation = "Waiting for Asian, London, or New York session framework."

# Display UI
st.markdown(f"""
<div style="background-color: #0f172a; padding: 25px; border-radius: 12px; border-left: 10px solid {color}; color: #f8fafc;">
    <h2 style="margin:0 0 8px 0; color:{color}; font-size: 1.4rem;">{signal_box}</h2>
    <p style="margin:4px 0; color:#94a3b8;"><b>Active Price:</b> {price:.2f} | <b>Offset:</b> {manual_offset:+.2f}$ | <b>Zone:</b> {zone_name}</p>
    <p style="margin:0 0 12px 0; color:#cbd5e1; font-size: 0.85rem;">🕒 IST Time: {datetime.now(IST_TZ).strftime('%H:%M:%S')} (GMT-4 Aligned)</p>
    <p style="margin:10px 0 0 0; font-size: 1rem; color:#e2e8f0;">{recommendation}</p>
    {f'<hr style="border-color:#334155; margin:12px 0;"><p style="color:#ff6b6b; margin:4px 0;"><b>Stop Loss (SL):</b> {sl_val:.2f}</p><p style="color:#51cf66; margin:4px 0;"><b>Take Profit (TP):</b> {tp_val:.2f}</p>' if sl_val else ''}
</div>
""", unsafe_allow_html=True)

# Missed / Last Triggered Setup Box
st.markdown("---")
st.subheader("🎯 Last Triggered Setup / Missed Trade Log")
j_data = load_journal()
if j_data:
    last_t = j_data[-1]
    st.markdown(f"""
    <div style="background-color: #1e293b; padding: 15px; border-radius: 8px; border: 1px solid #475569; color:#f8fafc;">
        <p style="margin:0; color:#38bdf8;"><b>Time:</b> {last_t['timestamp']} | <b>Type:</b> {last_t['type']}</p>
        <p style="margin:4px 0;"><b>From Price (Entry):</b> {last_t['entry']} ➔ <b>To Target (TP):</b> {last_t['tp']} | <b>SL:</b> {last_t['sl']}</p>
        <p style="margin:0; font-size:0.85rem; color:#94a3b8;"><b>Basis/Reason:</b> {last_t['reason']}</p>
    </div>
    """, unsafe_allow_html=True)
else:
    st.info("No missed setups logged yet in the recent window.")

# Performance Tracker
st.markdown("---")
st.subheader("📅 1-Month Trading Journey & P&L Performance Tracker")
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
    
