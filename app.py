import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import sys

# Add current directory to path for imports
sys.path.append('.')

from database import (
    init_database, get_latest_metrics, get_ticker_metrics, 
    get_positions, create_position, close_position, update_position_price,
    get_sp500_universe, save_universe, save_metrics, log_event
)
from data_fetcher import get_sp500_tickers, get_price_data, get_latest_price
from metrics import compute_projected_gain

# Initialize database
init_database()

# Page configuration
st.set_page_config(
    page_title="A1-MRE Rotational Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    .metric-card { 
        background-color: #f0f2f6; 
        padding: 20px; 
        border-radius: 10px; 
        margin: 10px 0;
    }
    .status-qualified { color: #00cc00; font-weight: bold; }
    .status-watch { color: #ff9900; font-weight: bold; }
    .status-excluded { color: #cc0000; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# Sidebar navigation
st.sidebar.title("A1-MRE Dashboard")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigate to:",
    ["Rotational Scan", "Ticker Detail", "Positions & Risk", "Performance & Modeling"]
)

st.sidebar.markdown("---")
st.sidebar.markdown("**Last Updated:**")
st.sidebar.markdown(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

# Page: Rotational Scan
if page == "Rotational Scan":
    st.title("🔄 Rotational Scan")
    st.markdown("Current S&P 500 leadership and A1-MRE qualification status")
    
    # Get latest metrics
    metrics = get_latest_metrics()
    
    if not metrics:
        st.warning("No metrics available. Run the data update script first.")
        st.info("To populate data, run: `python update_data.py`")
    else:
        df = pd.DataFrame(metrics)
        
        # Filters
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            sectors = ['All'] + sorted(df['sector'].unique())
            selected_sector = st.selectbox("Sector", sectors)
        
        with col2:
            rs_min = st.slider("RS Minimum", 0, 100, 0)
        
        with col3:
            vol_regimes = ['All', 'low', 'medium', 'high']
            selected_vol = st.multiselect("Volatility Regime", vol_regimes, default=['All'])
        
        with col4:
            statuses = ['All', 'qualified', 'watch', 'excluded']
            selected_status = st.multiselect("Status", statuses, default=['qualified', 'watch'])
        
        # Apply filters
        filtered_df = df.copy()
        
        if selected_sector != 'All':
            filtered_df = filtered_df[filtered_df['sector'] == selected_sector]
        
        if rs_min > 0:
            filtered_df = filtered_df[filtered_df['rs_score'] >= rs_min]
        
        if 'All' not in selected_vol:
            filtered_df = filtered_df[filtered_df['vol_regime'].isin(selected_vol)]
        
        if 'All' not in selected_status:
            filtered_df = filtered_df[filtered_df['status'].isin(selected_status)]
        
        # Sort by Entry Score descending
        filtered_df = filtered_df.sort_values('entry_score', ascending=False)
        
        # Display summary
        st.markdown(f"**Showing {len(filtered_df)} of {len(df)} stocks**")
        
        # Display table
        display_columns = [
            'ticker', 'name', 'sector', 'price', 'ytd_return', 'one_month_return', 
            'two_week_return', 'rs_score', 'momentum_persistence', 'vol_30d', 
            'atr_pct', 'entry_score', 'status'
        ]
        
        display_df = filtered_df[display_columns].copy()
        
        # Format columns
        display_df['price'] = display_df['price'].round(2)
        display_df['ytd_return'] = display_df['ytd_return'].round(2)
        display_df['one_month_return'] = display_df['one_month_return'].round(2)
        display_df['two_week_return'] = display_df['two_week_return'].round(2)
        display_df['rs_score'] = display_df['rs_score'].round(1)
        display_df['momentum_persistence'] = display_df['momentum_persistence'].round(1)
        display_df['vol_30d'] = display_df['vol_30d'].round(2)
        display_df['atr_pct'] = display_df['atr_pct'].round(2)
        display_df['entry_score'] = display_df['entry_score'].round(1)
        
        # Rename columns for display
        display_df.columns = [
            'Ticker', 'Name', 'Sector', 'Price', 'YTD %', '1M %', '2W %',
            'RS', 'Persistence', 'Vol 30d %', 'ATR %', 'Entry Score', 'Status'
        ]
        
        # Color status column
        def color_status(val):
            if val == 'qualified':
                return 'color: #00cc00; font-weight: bold'
            elif val == 'watch':
                return 'color: #ff9900; font-weight: bold'
            else:
                return 'color: #cc0000; font-weight: bold'
        
        styled_df = display_df.style.applymap(color_status, subset=['Status'])
        
        st.dataframe(styled_df, use_container_width=True, height=600)

# Page: Ticker Detail
elif page == "Ticker Detail":
    st.title("📈 Ticker Detail")
    
    # Ticker input
    ticker = st.text_input("Enter Ticker Symbol", value="AAPL").upper()
    
    if ticker:
        metrics = get_ticker_metrics(ticker)
        
        if not metrics:
            st.error(f"No data found for ticker {ticker}")
        else:
            # Header
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Ticker", metrics['ticker'])
            with col2:
                st.metric("Name", metrics['name'])
            with col3:
                st.metric("Sector", metrics['sector'])
            
            st.metric("Current Price", f"${metrics['price']:.2f}")
            
            # Price chart
            price_data = get_price_data(ticker, period="1y")
            
            if not price_data.empty:
                fig = go.Figure()
                
                # Price line
                fig.add_trace(go.Scatter(
                    x=price_data.index,
                    y=price_data['Close'],
                    mode='lines',
                    name='Price',
                    line=dict(color='#1f77b4', width=2)
                ))
                
                # Moving averages
                if len(price_data) >= 20:
                    ma20 = price_data['Close'].rolling(window=20).mean()
                    fig.add_trace(go.Scatter(
                        x=price_data.index,
                        y=ma20,
                        mode='lines',
                        name='20-day MA',
                        line=dict(color='#ff7f0e', width=1)
                    ))
                
                if len(price_data) >= 50:
                    ma50 = price_data['Close'].rolling(window=50).mean()
                    fig.add_trace(go.Scatter(
                        x=price_data.index,
                        y=ma50,
                        mode='lines',
                        name='50-day MA',
                        line=dict(color='#2ca02c', width=1)
                    ))
                
                if len(price_data) >= 200:
                    ma200 = price_data['Close'].rolling(window=200).mean()
                    fig.add_trace(go.Scatter(
                        x=price_data.index,
                        y=ma200,
                        mode='lines',
                        name='200-day MA',
                        line=dict(color='#d62728', width=1)
                    ))
                
                fig.update_layout(
                    title=f"{ticker} Price History",
                    xaxis_title="Date",
                    yaxis_title="Price ($)",
                    hovermode='x unified',
                    height=400
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            # Metrics panels
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Momentum")
                st.metric("YTD Return", f"{metrics['ytd_return']:.2f}%")
                st.metric("1-Month Return", f"{metrics['one_month_return']:.2f}%")
                st.metric("2-Week Return", f"{metrics['two_week_return']:.2f}%")
                st.metric("Momentum Persistence", f"{metrics['momentum_persistence']:.1f}")
                
                st.subheader("Relative Strength")
                st.metric("RS Score", f"{metrics['rs_score']:.1f}")
                st.metric("RS Trend", metrics['rs_trend'].title())
            
            with col2:
                st.subheader("Volatility")
                st.metric("30-Day Volatility", f"{metrics['vol_30d']:.2f}%")
                st.metric("ATR %", f"{metrics['atr_pct']:.2f}%")
                st.metric("Volatility Regime", metrics['vol_regime'].title())
                
                st.subheader("Earnings")
                if metrics['earnings_date']:
                    st.metric("Earnings Date", metrics['earnings_date'])
                    st.metric("Days to Earnings", metrics['days_to_earnings'])
                else:
                    st.info("Earnings date not available")
            
            # Entry decision box
            st.subheader("Entry Decision")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Entry Score", f"{metrics['entry_score']:.1f}")
                status_class = f"status-{metrics['status']}"
                st.markdown(f"<span class='{status_class}'>Status: {metrics['status'].upper()}</span>", 
                           unsafe_allow_html=True)
            
            with col2:
                st.subheader("Qualification Tags")
                tags = []
                if metrics['rs_score'] >= 80:
                    tags.append("✅ Strong RS (RS ≥ 80)")
                else:
                    tags.append("❌ Weak RS")
                
                if metrics['momentum_persistence'] >= 70:
                    tags.append("✅ Persistent momentum (≥ 70)")
                else:
                    tags.append("❌ Low persistence")
                
                if metrics['vol_regime'] == 'high':
                    tags.append("⚠ High volatility")
                else:
                    tags.append("✅ Acceptable volatility")
                
                if metrics['days_to_earnings'] and metrics['days_to_earnings'] <= 10:
                    tags.append("⚠ Earnings soon (≤ 10 days)")
                else:
                    tags.append("✅ Earnings not imminent")
                
                if metrics['entry_score'] >= 75:
                    tags.append("✅ Entry score above threshold")
                else:
                    tags.append("❌ Entry score below threshold")
                
                for tag in tags:
                    st.markdown(f"- {tag}")
            
            # Position actions
            st.subheader("Position Actions")
            
            # Check if position exists
            positions = get_positions(status='open')
            existing_position = next((p for p in positions if p['ticker'] == ticker), None)
            
            col1, col2 = st.columns(2)
            
            with col1:
                if not existing_position:
                    if st.button("Open Position", key=f"open_{ticker}"):
                        create_position(ticker, metrics['price'], metrics['rs_trend'], metrics['vol_regime'])
                        st.success(f"Position opened for {ticker} at ${metrics['price']:.2f}")
                        st.rerun()
                else:
                    st.info(f"Position already open for {ticker}")
            
            with col2:
                if existing_position:
                    if st.button("Mark Exit", key=f"exit_{ticker}"):
                        current_price = get_latest_price(ticker)
                        if current_price:
                            close_position(existing_position['id'], current_price, "Manual exit")
                            st.success(f"Position closed for {ticker} at ${current_price:.2f}")
                            st.rerun()

# Page: Positions & Risk
elif page == "Positions & Risk":
    st.title("⚠️ Positions & Risk")
    st.markdown("Monitor open positions and risk signals")
    
    # Update prices for open positions
    open_positions = get_positions(status='open')
    
    for pos in open_positions:
        current_price = get_latest_price(pos['ticker'])
        if current_price:
            update_position_price(pos['ticker'], current_price)
    
    # Refresh positions after update
    open_positions = get_positions(status='open')
    exit_required = get_positions(status='exit_required')
    
    all_active = open_positions + exit_required
    
    if not all_active:
        st.info("No open positions")
    else:
        st.markdown(f"**{len(all_active)} Active Position(s)**")
        
        # Create dataframe
        positions_data = []
        for pos in all_active:
            positions_data.append({
                'Ticker': pos['ticker'],
                'Entry Date': pos['entry_date'],
                'Entry Price': f"${pos['entry_price']:.2f}",
                'Current Price': f"${pos['current_price']:.2f}",
                'Stop Price': f"${pos['stop_price']:.2f}",
                'P&L %': f"{pos['pnl_pct']:.2f}%",
                'RS Trend': pos['rs_trend'].title(),
                'Vol Regime': pos['vol_regime'].title(),
                'Status': pos['status'].replace('_', ' ').title()
            })
        
        df = pd.DataFrame(positions_data)
        
        # Color coding
        def highlight_row(row):
            if row['Status'] == 'Exit Required':
                return ['background-color: #ffcccc'] * len(row)
            elif row['RS Trend'] == 'Falling' or row['Vol Regime'] == 'High':
                return ['background-color: #fff4cc'] * len(row)
            return [''] * len(row)
        
        styled_df = df.style.apply(highlight_row, axis=1)
        st.dataframe(styled_df, use_container_width=True)
        
        # Exit actions
        st.subheader("Exit Actions")
        
        for pos in exit_required:
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                st.warning(f"⚠️ {pos['ticker']} - Stop loss triggered!")
                st.markdown(f"Current: ${pos['current_price']:.2f} | Stop: ${pos['stop_price']:.2f}")
            
            with col2:
                st.markdown(f"P&L: {pos['pnl_pct']:.2f}%")
            
            with col3:
                if st.button("Confirm Exit", key=f"confirm_{pos['id']}"):
                    close_position(pos['id'], pos['current_price'], "5_percent_rule")
                    st.success(f"Position closed for {pos['ticker']}")
                    st.rerun()

# Page: Performance & Modeling
elif page == "Performance & Modeling":
    st.title("📊 Performance & Modeling")
    st.markdown("A1-MRE performance vs S&P 500 and modelled projected gain bands")
    
    # Get qualified stocks
    metrics = get_latest_metrics()
    qualified = [m for m in metrics if m['status'] == 'qualified'] if metrics else []
    
    if not qualified:
        st.info("No qualified stocks available")
    else:
        # Projected gain modeling table
        st.subheader("Projected Gain Modeling (Qualified Stocks)")
        st.markdown("*Modelled projections only - not financial advice*")
        
        modeling_data = []
        for m in qualified:
            projected = compute_projected_gain(
                m['momentum_persistence'], 
                m['vol_regime'], 
                m['rs_trend']
            )
            
            modeling_data.append({
                'Ticker': m['ticker'],
                'RS': f"{m['rs_score']:.1f}",
                'Persistence': f"{m['momentum_persistence']:.1f}",
                'Vol Regime': m['vol_regime'].title(),
                'Trend Factor': {'rising': 1.0, 'flat': 0.8, 'falling': 0.6}.get(m['rs_trend'], 0.8),
                'Vol Factor': {'low': 1.0, 'medium': 0.8, 'high': 0.6}.get(m['vol_regime'], 0.8),
                'Projected Gain Band': f"{projected['lower']:.1f}% to {projected['upper']:.1f}%",
                'Confidence': projected['confidence']
            })
        
        df_model = pd.DataFrame(modeling_data)
        st.dataframe(df_model, use_container_width=True)
        
        # Summary stats (placeholder - would need historical trade data)
        st.subheader("Performance Summary")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Return", "N/A", help="Requires historical trade data")
        
        with col2:
            st.metric("Max Drawdown", "N/A", help="Requires historical trade data")
        
        with col3:
            st.metric("Win Rate", "N/A", help="Requires historical trade data")
        
        st.info("Performance metrics will be populated as trade history accumulates")

# Footer
st.markdown("---")
st.markdown("""
**Disclaimer:** This dashboard is for informational purposes only. The A1-MRE strategy and all projections are modelled outputs, not financial advice. 
Past performance does not guarantee future results. Always conduct your own research and consult with a qualified financial advisor before making investment decisions.
""", unsafe_allow_html=True)
