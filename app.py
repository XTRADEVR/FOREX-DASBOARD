import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime
import time

st.set_page_config(page_title="GROKIUS AI Forex LIVE", page_icon="📈", layout="wide")

# --- LOAD STYLE.CSS ---
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# --- FUNGSI AI SIGNAL ---
def hitung_sinyal_ai(df):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    rsi_now = float(rsi.iloc[-1])
    ma_fast = float(df['Close'].rolling(window=9).mean().iloc[-1])
    ma_slow = float(df['Close'].rolling(window=21).mean().iloc[-1])
    ema12 = df['Close'].ewm(span=12).mean()
    ema26 = df['Close'].ewm(span=26).mean()
    macd = ema12 - ema26
    macd_now = float(macd.iloc[-1])
    signal_line = float(macd.ewm(span=9).mean().iloc[-1])

    skor_buy, skor_sell, alasan = 0, 0, []
    if rsi_now < 35:
        skor_buy += 1; alasan.append(f"RSI Oversold ({rsi_now:.1f}) -> Potensi Naik")
    elif rsi_now > 65:
        skor_sell += 1; alasan.append(f"RSI Overbought ({rsi_now:.1f}) -> Potensi Turun")
    if ma_fast > ma_slow:
        skor_buy += 1; alasan.append("MA 9 di atas MA 21 -> Trend Naik")
    else:
        skor_sell += 1; alasan.append("MA 9 di bawah MA 21 -> Trend Turun")
    if macd_now > signal_line:
        skor_buy += 1; alasan.append("MACD Bullish -> Momentum Naik")
    else:
        skor_sell += 1; alasan.append("MACD Bearish -> Momentum Turun")

    if skor_buy >= 2: return "BUY", f"Confidence {skor_buy}/3", alasan, rsi_now
    elif skor_sell >= 2: return "SELL", f"Confidence {skor_sell}/3", alasan, rsi_now
    else: return "HOLD / WAIT", "Confidence 1/3", alasan, rsi_now

# --- SIDEBAR ---
with st.sidebar:
    st.header("Controls - LIVE")
    pair_nama = st.selectbox("Select Pair", ["EUR/USD", "GBP/USD", "USD/JPY", "XAU/USD", "GBP/JPY"])
    lot = st.slider("Lot Size", 0.01, 2.0, 0.50)
    risk = st.slider("Risk %", 1, 100, 25)
    tf = st.selectbox("Timeframe", ["15m", "1h", "4h", "1d"], index=1)
    auto = st.toggle("Auto-Refresh 30 Detik", value=True)

symbol_map = {"EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "USDJPY=X", "XAU/USD": "GC=F", "GBP/JPY": "GBPJPY=X"}
interval_map = {"15m": "15m", "1h": "60m", "4h": "1h", "1d": "1d"}
symbol = symbol_map[pair_nama]

@st.cache_data(ttl=30)
def get_live_data(symbol, interval):
    df = yf.download(symbol, period="5d", interval=interval, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df.dropna()

try:
    df = get_live_data(symbol, interval_map[tf])
    price_now = float(df['Close'].iloc[-1])
    price_open = float(df['Open'].iloc[0])
    change_pct = ((price_now - price_open) / price_open) * 100

    st.title("GROKIUS AI Forex Dashboard - LIVE")
    st.caption(f"Pair: {pair_nama} | Symbol: {symbol} | Update: {datetime.now().strftime('%H:%M:%S')} WIB | Source: Yahoo Finance")

    sinyal, confidence, alasan, rsi = hitung_sinyal_ai(df)
    c_signal, c_detail = st.columns([1, 2])
    with c_signal:
        css_class = "signal-buy" if sinyal=="BUY" else "signal-sell" if sinyal=="SELL" else "signal-hold"
        emoji = "🟢" if sinyal=="BUY" else "🔴" if sinyal=="SELL" else "🟡"
        st.markdown(f'<div class="{css_class}">{emoji} {sinyal}<br><span style="font-size:16px">{confidence}</span></div>', unsafe_allow_html=True)
    with c_detail:
        st.subheader("Kenapa AI Bilang Gitu?")
        for a in alasan: st.write(f"- {a}")
        st.write(f"- RSI Saat Ini: **{rsi:.2f}**")
        st.write(f"- Lot: **{lot}** | Risk: **{risk}%** | TP: **{price_now*1.001:.4f}** | SL: **{price_now*0.999:.4f}**")

    c1, c2, c3 = st.columns(3)
    c1.metric(f"{pair_nama} Price LIVE", f"{price_now:.4f}", f"{change_pct:.2f}%")
    c2.metric("RSI (14)", f"{rsi:.1f}", "Oversold <30, Overbought >70")
    c3.metric("AI Signal", sinyal, confidence)

    st.subheader(f"{pair_nama} • Live Candlestick - {tf}")
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], increasing_line_color='#00C087', decreasing_line_color='#FF4B4B')])
    fig.add_trace(go.Scatter(x=df.index, y=df['Close'].rolling(9).mean(), line=dict(color='yellow', width=1), name='MA 9'))
    fig.add_trace(go.Scatter(x=df.index, y=df['Close'].rolling(21).mean(), line=dict(color='blue', width=1), name='MA 21'))
    fig.update_layout(template="plotly_dark", height=500, paper_bgcolor="#0E1117", plot_bgcolor="#0E1117", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    if auto:
        time.sleep(30)
        st.rerun()
except Exception as e:
    st.error(f"Gagal ambil data live: {e}")
