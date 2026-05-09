import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
from datetime import datetime

# 1. Configuration - Add your specific Buy Dates here
portfolio_data = [
    {"ticker": "MU", "qty": 10, "buy_price": 85.50, "buy_date": "2024-01-15"},
    {"ticker": "MRVL", "qty": 15, "buy_price": 68.20, "buy_date": "2024-02-10"},
    {"ticker": "IREDA.NS", "qty": 1213, "buy_price": 60.00, "buy_date": "2023-12-18"}
]

@st.cache_data(ttl=3600)
def get_portfolio_metrics():
    results = []
    for stock in portfolio_data:
        ticker = yf.Ticker(stock['ticker'])
        
        # Get Current Price
        current_data = ticker.history(period="1d")
        current_price = current_data['Close'].iloc[-1]
        
        # Calculate Metrics
        cost_basis = stock['qty'] * stock['buy_price']
        market_value = stock['qty'] * current_price
        total_gain = market_value - cost_basis
        percentage_gain = (total_gain / cost_basis) * 100
        
        # Calculate Days Held
        days_held = (datetime.now() - datetime.strptime(stock['buy_date'], "%Y-%m-%d")).days
        
        results.append({
            "Ticker": stock['ticker'],
            "Buy Date": stock['buy_date'],
            "Days Held": days_held,
            "Cost Basis": round(cost_basis, 2),
            "Current Value": round(market_value, 2),
            "Gain/Loss": round(total_gain, 2),
            "Return %": round(percentage_gain, 2)
        })
    return pd.DataFrame(results)


@st.cache_data
def get_historical_gains():
    all_history = pd.DataFrame()
    
    for stock in portfolio_data:
        ticker = stock['ticker']
        # 1. Download data
        # We use group_by='column' to ensure a consistent structure
        data = yf.download(ticker, start=stock['buy_date'], progress=False)
        
        if data.empty:
            continue

        # 2. Extract 'Close' column safely
        # yfinance often returns a MultiIndex (Price, Ticker). We flatten it.
        if isinstance(data.columns, pd.MultiIndex):
            close_prices = data['Close'][ticker]
        else:
            close_prices = data['Close']
        
        # 3. Calculate daily gain: (Price - Buy Price) * Qty
        gain_series = (close_prices - stock['buy_price']) * stock['qty']
        gain_df = gain_series.to_frame(name=f'{ticker} Gain')
        
        # 4. Merge into master dataframe
        if all_history.empty:
            all_history = gain_df
        else:
            all_history = all_history.join(gain_df, how='outer')
            
    # Use ffill() to handle holidays/weekends where one market is open and others aren't
    return all_history.ffill()

# --- Streamlit UI ---
st.set_page_config(page_title="Portfolio Tracker", layout="wide")

st.title("📈 Cumulative Gains Over Time")

history_df = get_historical_gains()

# Plot 1: Individual Stock Gains Over Time
st.subheader("Daily Gain per Stock ($)")
fig_daily = px.line(history_df, 
                    labels={"value": "Unrealized Gain ($)", "Date": "Date"},
                    title="Growth of Gains Since Purchase")
st.plotly_chart(fig_daily, use_container_width=True)

# Plot 2: Total Portfolio Gain Over Time
st.subheader("Total Portfolio Performance")
history_df['Total Portfolio Gain'] = history_df.sum(axis=1)
fig_total = px.area(history_df, y='Total Portfolio Gain', 
                    color_discrete_sequence=['#00CC96'],
                    title="Aggregate Portfolio Gain ($)")
st.plotly_chart(fig_total, use_container_width=True)


df = get_portfolio_metrics()

st.title("📊 Personal Alpha Dashboard")
st.markdown(f"**Tracking Performance since earliest Buy Date:** {df['Buy Date'].min()}")

# Metrics Row
c1, c2, c3, c4 = st.columns(4)
total_inv = df['Cost Basis'].sum()
total_val = df['Current Value'].sum()
total_gain = total_val - total_inv

c1.metric("Total Invested", f"${total_inv:,.2f}")
c2.metric("Portfolio Value", f"${total_val:,.2f}")
c3.metric("Total Gain", f"${total_gain:,.2f}", delta=f"{(total_gain/total_inv*100):.2f}%")
c4.metric("Avg Days Held", int(df['Days Held'].mean()))

# Visualization: Return since Buy Date
st.subheader("Performance Since Purchase")
fig = px.bar(df, x='Ticker', y='Return %', color='Return %',
             text='Return %', title="Percentage Gain per Position",
             color_continuous_scale='Greens' if total_gain > 0 else 'Reds')
st.plotly_chart(fig, use_container_width=True)

st.dataframe(df.sort_values("Return %", ascending=False), use_container_width=True)
