import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
from datetime import datetime

# 1. Configuration - Add your specific Buy Dates here
portfolio_data = [
    {"ticker": "HDFCBANK.NS", "qty": 38, "buy_price": 790.00, "buy_date": "2026-04-27"},
    {"ticker": "HDFCBANK.NS", "qty": 38, "buy_price": 775.95, "buy_date": "2026-05-06"},
    {"ticker": "HDFCBANK.NS", "qty": 25, "buy_price": 779.40, "buy_date": "2026-05-08"},
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
    # 1. Get unique tickers and their earliest buy date
    ledger = pd.DataFrame(portfolio_data)
    ledger['buy_date'] = pd.to_datetime(ledger['buy_date'])
    unique_tickers = ledger['ticker'].unique()
    
    all_history = pd.DataFrame()

    for ticker in unique_tickers:
        # Get all transactions for this ticker
        trades = ledger[ledger['ticker'] == ticker].sort_values('buy_date')
        
        # Download price history starting from the very first purchase
        first_buy = trades['buy_date'].min()
        data = yf.download(ticker, start=first_buy, progress=False)
        
        if data.empty: continue
        
        # Flatten MultiIndex if necessary
        prices = data['Close'][ticker] if isinstance(data.columns, pd.MultiIndex) else data['Close']
        prices = prices.to_frame(name='Price')
        
        # 2. Build daily position metrics
        prices['Total_Qty'] = 0.0
        prices['Total_Cost'] = 0.0
        
        for _, trade in trades.iterrows():
            # Add qty and cost to all dates on/after the purchase date
            mask = prices.index >= trade['buy_date']
            prices.loc[mask, 'Total_Qty'] += trade['qty']
            prices.loc[mask, 'Total_Cost'] += (trade['qty'] * trade['buy_price'])
            
        # 3. Calculate Running Average Price and Gain
        prices['Avg_Price'] = prices['Total_Cost'] / prices['Total_Qty']
        prices[f'{ticker} Gain'] = (prices['Price'] - prices['Avg_Price']) * prices['Total_Qty']
        
        # Merge into master df
        if all_history.empty:
            all_history = prices[[f'{ticker} Gain']]
        else:
            all_history = all_history.join(prices[[f'{ticker} Gain']], how='outer')
            
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
