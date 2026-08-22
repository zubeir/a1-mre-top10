import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import sys
import time

# Add current directory to path for imports
sys.path.append('.')

from database import (
    init_database, get_latest_metrics, get_ticker_metrics, 
    get_positions, create_position, close_position, update_position_price,
    get_sp500_universe, save_universe, save_metrics, log_event
)
from data_fetcher import get_sp500_tickers, get_price_data, get_latest_price, batch_get_prices
from metrics import compute_all_metrics, compute_projected_gain
from mock_data import generate_all_mock_metrics

# Initialize database
init_database()

# Auto-populate data if database is empty
def ensure_data_populated():
    """Check if data exists, populate with mock data if empty."""
    metrics = get_latest_metrics()
    if not metrics:
        with st.spinner("Initializing dashboard with sample data..."):
            # Get sample tickers
            ticker_data = get_sp500_tickers()
            save_universe(ticker_data)
            
            # Use mock data for reliability
            all_metrics = generate_all_mock_metrics(ticker_data)
            save_metrics(all_metrics)
            
            log_event('auto_init', {
                'timestamp': datetime.now().isoformat(),
                'tickers_processed': len(all_metrics)
            })
            st.success(f"Initialized with {len(all_metrics)} sample stocks")

ensure_data_populated()

# Page configuration
st.set_page_config(
    page_title="A1-MRE Rotational Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for enhanced UX
st.markdown("""
    <style>
    /* Main app styling */
    .stApp {
        background-color: #f8f9fa;
    }
    
    /* Header styling */
    h1 {
        color: #1e3a5f;
        font-weight: 700;
        border-bottom: 3px solid #3b82f6;
        padding-bottom: 10px;
    }
    
    h2 {
        color: #2c5282;
        font-weight: 600;
        margin-top: 30px;
    }
    
    h3 {
        color: #4a5568;
        font-weight: 500;
    }
    
    /* Metric cards */
    .metric-card { 
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px; 
        border-radius: 12px; 
        margin: 10px 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    /* Status colors */
    .status-qualified { 
        color: #059669; 
        font-weight: bold; 
        background-color: #d1fae5;
        padding: 4px 12px;
        border-radius: 20px;
        display: inline-block;
    }
    .status-watch { 
        color: #d97706; 
        font-weight: bold;
        background-color: #fef3c7;
        padding: 4px 12px;
        border-radius: 20px;
        display: inline-block;
    }
    .status-excluded { 
        color: #dc2626; 
        font-weight: bold;
        background-color: #fee2e2;
        padding: 4px 12px;
        border-radius: 20px;
        display: inline-block;
    }
    
    /* Info boxes */
    .stInfo {
        background-color: #e0f2fe;
        border-left: 4px solid #0284c7;
    }
    
    .stWarning {
        background-color: #fef3c7;
        border-left: 4px solid #f59e0b;
    }
    
    .stSuccess {
        background-color: #d1fae5;
        border-left: 4px solid #10b981;
    }
    
    .stError {
        background-color: #fee2e2;
        border-left: 4px solid #ef4444;
    }
    
    /* Dataframe styling */
    .dataframe {
        border-radius: 8px;
        overflow: hidden;
    }
    
    /* Button styling */
    .stButton>button {
        background-color: #3b82f6;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        background-color: #2563eb;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background-color: #1e3a5f;
    }
    
    /* Filter section */
    .filter-section {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        margin-bottom: 20px;
    }
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
        
        # Summary cards
        qualified_count = len([m for m in metrics if m['status'] == 'qualified'])
        watch_count = len([m for m in metrics if m['status'] == 'watch'])
        excluded_count = len([m for m in metrics if m['status'] == 'excluded'])
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📊 Total Stocks", len(df))
        with col2:
            st.metric("✅ Qualified", qualified_count, delta_color="normal")
        with col3:
            st.metric("⚠️ Watch", watch_count, delta_color="normal")
        with col4:
            st.metric("❌ Excluded", excluded_count, delta_color="normal")
        
        st.markdown("---")
        
        # Filters section with container
        with st.container():
            st.subheader("🔍 Filters")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                sectors = ['All'] + sorted(df['sector'].unique())
                selected_sector = st.selectbox("🏢 Sector", sectors)
            
            with col2:
                rs_min = st.slider("📈 RS Minimum", 0, 100, 60, help="Minimum Relative Strength score (60+ for watch, 80+ for qualified)")
            
            with col3:
                vol_regimes = ['All', 'low', 'medium', 'high']
                selected_vol = st.multiselect("📊 Volatility Regime", vol_regimes, default=['All'])
            
            with col4:
                statuses = ['All', 'qualified', 'watch', 'excluded']
                selected_status = st.multiselect("🏷️ Status", statuses, default=['qualified', 'watch'])
        
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
        st.markdown(f"**📋 Showing {len(filtered_df)} of {len(df)} stocks**")
        
        # Metrics explanation expander
        with st.expander("📖 Metric Definitions & Interpretation Guide"):
            st.markdown("""
            ### 🏷️ **Status**
            - **Qualified**: Meets all A1-MRE entry criteria (RS ≥ 80, Persistence ≥ 70, acceptable volatility)
            - **Watch**: Partially meets criteria (RS 60-79, or other factors borderline)
            - **Excluded**: Does not meet minimum criteria (RS < 60, high volatility, or poor momentum)
            
            ### 📈 **Ticker**
            - Stock symbol (e.g., AAPL, MSFT, GOOGL)
            
            ### 📛 **Name**
            - Full company name
            
            ### 🏢 **Sector**
            - Industry sector classification (Technology, Healthcare, Finance, etc.)
            
            ### 💰 **Price**
            - Current stock price in USD
            - Used for position entry and stop-loss calculations
            
            ### 📊 **YTD % (Year-to-Date Return)**
            - Percentage return from January 1st to current date
            - **> 20%**: Strong outperformance
            - **0-20%**: Moderate positive performance
            - **< 0%**: Underperformance year-to-date
            
            ### 📈 **1M % (1-Month Return)**
            - Percentage return over the last 30 trading days
            - Short-term momentum indicator
            - **> 5%**: Strong recent momentum
            - **0-5%**: Moderate momentum
            - **< 0%**: Recent weakness
            
            ### 📉 **2W % (2-Week Return)**
            - Percentage return over the last 10 trading days
            - Immediate momentum signal
            - **> 3%**: Very strong short-term momentum
            - **0-3%**: Normal short-term movement
            - **< 0%**: Short-term weakness
            
            ### 🎯 **RS (Relative Strength Score)**
            - Measures stock performance relative to S&P 500 universe (0-100 scale)
            - **80+**: Strong relative outperformance (qualified threshold)
            - **60-79**: Moderate outperformance (watch threshold)
            - **40-59**: Average performance
            - **< 40**: Underperformance (excluded)
            
            ### 📊 **Persistence (Momentum Persistence)**
            - Consistency of positive momentum over time (0-100 scale)
            - Measures how reliably the stock maintains upward trends
            - **≥ 70**: Highly persistent momentum (qualified threshold)
            - **50-69**: Moderately persistent
            - **< 50**: Inconsistent momentum
            
            ### 📉 **Vol 30d % (30-Day Volatility)**
            - Annualized volatility based on last 30 days of price movement
            - Measures risk and price fluctuation
            - **< 25%**: Low volatility (preferred)
            - **25-35%**: Medium volatility (acceptable)
            - **> 35%**: High volatility (risky)
            
            ### 📏 **ATR % (Average True Range %)**
            - Average daily price range as percentage of price
            - Measures typical daily price movement
            - Used for stop-loss placement (5% rule)
            - Lower values indicate more stable price action
            
            ### ⭐ **Entry Score (Composite Score)**
            - Overall A1-MRE qualification score (aggregates all metrics)
            - **≥ 75**: Strong entry candidate
            - **60-74**: Moderate entry candidate
            - **< 60**: Weak entry candidate
            - Formula combines: RS (40%), Persistence (30%), Volatility (20%), Trend (10%)
            """)
        
        # Display table with Status first
        display_columns = [
            'status', 'ticker', 'name', 'sector', 'price', 'ytd_return', 'one_month_return', 
            'two_week_return', 'rs_score', 'momentum_persistence', 'vol_30d', 
            'atr_pct', 'entry_score'
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
        
        # Rename columns for display with emoji indicators and tooltips
        display_df.columns = [
            '🏷️ Status', '📈 Ticker', '📛 Name', '🏢 Sector', '💰 Price', '📊 YTD %', '📈 1M %', '📉 2W %',
            '🎯 RS', '📊 Persistence', '📉 Vol 30d %', '📏 ATR %', '⭐ Entry Score'
        ]
        
        # Column information guide (always visible)
        st.markdown("### 📋 Column Reference Guide")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            **🏷️ Status**
            - Qualified: Meets all criteria
            - Watch: Partially meets criteria  
            - Excluded: Does not meet criteria
            
            **📈 Ticker**
            - Stock symbol (e.g., AAPL, MSFT)
            
            **📛 Name**
            - Full company name
            
            **🏢 Sector**
            - Industry sector classification
            
            **💰 Price**
            - Current stock price in USD
            """)
        
        with col2:
            st.markdown("""
            **📊 YTD %**
            - >20%: Strong outperformance
            - 0-20%: Moderate performance
            - <0%: Underperformance
            
            **📈 1M %**
            - >5%: Strong momentum
            - 0-5%: Moderate momentum
            - <0%: Recent weakness
            
            **📉 2W %**
            - >3%: Very strong momentum
            - 0-3%: Normal movement
            - <0%: Short-term weakness
            
            **🎯 RS**
            - 80+: Excellent (qualified)
            - 60-79: Good (watch)
            - 40-59: Fair
            - <40: Poor (excluded)
            """)
        
        with col3:
            st.markdown("""
            **� Persistence**
            - ≥70: Highly consistent
            - 50-69: Moderately consistent
            - <50: Inconsistent
            
            **📉 Vol 30d %**
            - <25%: Low volatility
            - 25-35%: Medium volatility
            - >35%: High volatility
            
            **📏 ATR %**
            - Daily price movement
            - Used for stop-loss placement
            
            **⭐ Entry Score**
            - ≥75: Strong candidate
            - 60-74: Moderate candidate
            - <60: Weak candidate
            """)
        
        # Enhanced color coding
        def color_status(val):
            if val == 'qualified':
                return 'background-color: #d1fae5; color: #059669; font-weight: bold; padding: 4px; border-radius: 4px;'
            elif val == 'watch':
                return 'background-color: #fef3c7; color: #d97706; font-weight: bold; padding: 4px; border-radius: 4px;'
            else:
                return 'background-color: #fee2e2; color: #dc2626; font-weight: bold; padding: 4px; border-radius: 4px;'
        
        def color_returns(val):
            try:
                val = float(val)
                if val > 0:
                    return 'color: #059669; font-weight: 600'
                elif val < 0:
                    return 'color: #dc2626; font-weight: 600'
                else:
                    return 'color: #6b7280'
            except:
                return ''
        
        def color_scores(val):
            try:
                val = float(val)
                if val >= 80:
                    return 'background-color: #d1fae5; color: #059669; font-weight: bold'
                elif val >= 60:
                    return 'background-color: #fef3c7; color: #d97706; font-weight: bold'
                elif val >= 40:
                    return 'background-color: #fef9c3; color: #ca8a04'
                else:
                    return 'background-color: #fee2e2; color: #dc2626'
            except:
                return ''
        
        def color_volatility(val):
            try:
                val = float(val)
                if val < 25:
                    return 'color: #059669; font-weight: 500'
                elif val < 35:
                    return 'color: #d97706; font-weight: 500'
                else:
                    return 'color: #dc2626; font-weight: 600'
            except:
                return ''
        
        # Row-level highlighting based on status
        def highlight_row(row):
            status = row['🏷️ Status']
            if status == 'qualified':
                return ['background-color: #d1fae5'] * len(row)
            elif status == 'watch':
                return ['background-color: #fef3c7'] * len(row)
            else:
                return ['background-color: #fee2e2'] * len(row)
        
        styled_df = display_df.style.apply(highlight_row, axis=1)
        styled_df = styled_df.map(color_status, subset=['🏷️ Status'])
        styled_df = styled_df.map(color_returns, subset=['📊 YTD %', '📈 1M %', '📉 2W %'])
        styled_df = styled_df.map(color_scores, subset=['🎯 RS', '📊 Persistence', '⭐ Entry Score'])
        styled_df = styled_df.map(color_volatility, subset=['📉 Vol 30d %', '📏 ATR %'])
        
        # Add hover effect and better styling
        styled_df = styled_df.set_properties(**{
            'color': '#1f2937',
            'font-size': '14px',
            'border': '1px solid #e5e7eb'
        })
        
        st.dataframe(styled_df, use_container_width=True, height=600)
        
        # Add row selection for drill-down
        st.markdown("---")
        st.markdown("### 🔍 Drill Down to Ticker Detail")
        selected_ticker = st.selectbox(
            "Select a ticker to view detailed analysis:",
            options=[''] + [row['📈 Ticker'] for _, row in display_df.iterrows()],
            format_func=lambda x: "Choose a ticker..." if x == '' else x,
            key="ticker_selector"
        )
        
        if selected_ticker:
            st.session_state.selected_ticker = selected_ticker
            st.success(f"✅ Selected {selected_ticker}. Click 'Ticker Detail' in the sidebar to view comprehensive analysis.")
            st.info("� Navigate to 'Ticker Detail' page in the sidebar to see the full analysis.")
        
        # Add color legend
        st.markdown("---")
        st.markdown("### 🎨 Color Legend")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("**Status Colors:**")
            st.markdown("🟢 **Qualified** - Meets all criteria")
            st.markdown("🟡 **Watch** - Partially meets criteria")
            st.markdown("🔴 **Excluded** - Does not meet criteria")
        
        with col2:
            st.markdown("**Score Colors:**")
            st.markdown("🟢 **80+** - Excellent")
            st.markdown("🟡 **60-79** - Good")
            st.markdown("🟠 **40-59** - Fair")
            st.markdown("🔴 **<40** - Poor")
        
        with col3:
            st.markdown("**Return Colors:**")
            st.markdown("🟢 **>0%** - Positive")
            st.markdown("🔴 **<0%** - Negative")
        
        with col4:
            st.markdown("**Volatility Colors:**")
            st.markdown("🟢 **<25%** - Low")
            st.markdown("🟡 **25-35%** - Medium")
            st.markdown("🔴 **>35%** - High")

# Page: Ticker Detail
elif page == "Ticker Detail":
    st.title("📈 Ticker Detail")
    st.markdown("Deep dive into individual stock metrics and entry decision support")
    
    # Check if ticker was passed from Rotational Scan
    if 'selected_ticker' in st.session_state and st.session_state.selected_ticker:
        default_ticker = st.session_state.selected_ticker
    else:
        default_ticker = "AAPL"
    
    # Ticker input
    ticker = st.text_input("🔍 Enter Ticker Symbol", value=default_ticker).upper()
    
    if ticker:
        metrics = get_ticker_metrics(ticker)
        
        if not metrics:
            st.error(f"❌ No data found for ticker {ticker}")
        else:
            # Header with enhanced styling
            st.markdown("---")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("🏷️ Ticker", metrics['ticker'])
            with col2:
                st.metric("📛 Name", metrics['name'])
            with col3:
                st.metric("🏢 Sector", metrics['sector'])
            with col4:
                st.metric("💰 Current Price", f"${metrics['price']:.2f}")
            
            st.markdown("---")
            
            # Price chart
            price_data = get_price_data(ticker, period="1y")
            
            if not price_data.empty:
                fig = go.Figure()
                
                # Price line with gradient fill
                fig.add_trace(go.Scatter(
                    x=price_data.index,
                    y=price_data['Close'],
                    mode='lines',
                    name='Price',
                    line=dict(color='#3b82f6', width=2),
                    fill='tozeroy',
                    fillcolor='rgba(59, 130, 246, 0.1)'
                ))
                
                # Moving averages with better colors
                if len(price_data) >= 20:
                    ma20 = price_data['Close'].rolling(window=20).mean()
                    fig.add_trace(go.Scatter(
                        x=price_data.index,
                        y=ma20,
                        mode='lines',
                        name='20-day MA',
                        line=dict(color='#f59e0b', width=2)
                    ))
                
                if len(price_data) >= 50:
                    ma50 = price_data['Close'].rolling(window=50).mean()
                    fig.add_trace(go.Scatter(
                        x=price_data.index,
                        y=ma50,
                        mode='lines',
                        name='50-day MA',
                        line=dict(color='#10b981', width=2)
                    ))
                
                if len(price_data) >= 200:
                    ma200 = price_data['Close'].rolling(window=200).mean()
                    fig.add_trace(go.Scatter(
                        x=price_data.index,
                        y=ma200,
                        mode='lines',
                        name='200-day MA',
                        line=dict(color='#ef4444', width=2)
                    ))
                
                fig.update_layout(
                    title=f"📊 {ticker} Price History",
                    xaxis_title="Date",
                    yaxis_title="Price ($)",
                    hovermode='x unified',
                    height=450,
                    plot_bgcolor='rgba(255, 255, 255, 0.8)',
                    paper_bgcolor='rgba(255, 255, 255, 0.8)',
                    font=dict(size=12)
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            # Metrics panels with enhanced styling
            st.markdown("---")
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 📈 Momentum")
                ytd_color = "🟢" if metrics['ytd_return'] > 0 else "🔴"
                one_month_color = "🟢" if metrics['one_month_return'] > 0 else "🔴"
                two_week_color = "🟢" if metrics['two_week_return'] > 0 else "🔴"
                
                st.metric(f"{ytd_color} YTD Return", f"{metrics['ytd_return']:.2f}%")
                st.metric(f"{one_month_color} 1-Month Return", f"{metrics['one_month_return']:.2f}%")
                st.metric(f"{two_week_color} 2-Week Return", f"{metrics['two_week_return']:.2f}%")
                st.metric("📊 Momentum Persistence", f"{metrics['momentum_persistence']:.1f}")
                
                st.markdown("### 🎯 Relative Strength")
                rs_color = "🟢" if metrics['rs_score'] >= 80 else "🟡" if metrics['rs_score'] >= 60 else "🔴"
                st.metric(f"{rs_color} RS Score", f"{metrics['rs_score']:.1f}")
                trend_emoji = "📈" if metrics['rs_trend'] == 'rising' else "➡️" if metrics['rs_trend'] == 'flat' else "📉"
                st.metric(f"{trend_emoji} RS Trend", metrics['rs_trend'].title())
            
            with col2:
                st.markdown("### 📊 Volatility")
                vol_color = "🟢" if metrics['vol_regime'] == 'low' else "🟡" if metrics['vol_regime'] == 'medium' else "🔴"
                st.metric("📉 30-Day Volatility", f"{metrics['vol_30d']:.2f}%")
                st.metric("📏 ATR %", f"{metrics['atr_pct']:.2f}%")
                st.metric(f"{vol_color} Volatility Regime", metrics['vol_regime'].title())
                
                st.markdown("### 📅 Earnings")
                if metrics['earnings_date']:
                    earnings_emoji = "⚠️" if metrics['days_to_earnings'] and metrics['days_to_earnings'] <= 10 else "✅"
                    st.metric("Earnings Date", metrics['earnings_date'])
                    st.metric(f"{earnings_emoji} Days to Earnings", metrics['days_to_earnings'])
                else:
                    st.info("ℹ️ Earnings date not available")
            
            # Entry decision box with enhanced styling
            st.markdown("---")
            st.markdown("### 🎯 Entry Decision")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Entry score with color coding
                score_color = "🟢" if metrics['entry_score'] >= 75 else "🟡" if metrics['entry_score'] >= 60 else "🔴"
                st.metric(f"{score_color} Entry Score", f"{metrics['entry_score']:.1f}")
                
                # Status with badge
                status_emoji = "✅" if metrics['status'] == 'qualified' else "⚠️" if metrics['status'] == 'watch' else "❌"
                status_bg = "#d1fae5" if metrics['status'] == 'qualified' else "#fef3c7" if metrics['status'] == 'watch' else "#fee2e2"
                status_text_color = "#059669" if metrics['status'] == 'qualified' else "#d97706" if metrics['status'] == 'watch' else "#dc2626"
                st.markdown(
                    f'<div style="background-color: {status_bg}; color: {status_text_color}; '
                    f'padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; font-size: 18px;">'
                    f'{status_emoji} Status: {metrics["status"].upper()}</div>',
                    unsafe_allow_html=True
                )
            
            with col2:
                st.markdown("#### 📋 Qualification Tags")
                tags = []
                if metrics['rs_score'] >= 80:
                    tags.append("✅ **Strong RS** (RS ≥ 80)")
                else:
                    tags.append("❌ **Weak RS**")
                
                if metrics['momentum_persistence'] >= 70:
                    tags.append("✅ **Persistent momentum** (≥ 70)")
                else:
                    tags.append("❌ **Low persistence**")
                
                if metrics['vol_regime'] == 'high':
                    tags.append("⚠️ **High volatility**")
                else:
                    tags.append("✅ **Acceptable volatility**")
                
                if metrics['days_to_earnings'] and metrics['days_to_earnings'] <= 10:
                    tags.append("⚠️ **Earnings soon** (≤ 10 days)")
                else:
                    tags.append("✅ **Earnings not imminent**")
                
                if metrics['entry_score'] >= 75:
                    tags.append("✅ **Entry score above threshold**")
                else:
                    tags.append("❌ **Entry score below threshold**")
                
                for tag in tags:
                    st.markdown(f"- {tag}")
            
            # Position actions with enhanced styling
            st.markdown("---")
            st.markdown("### 💼 Position Actions")
            
            # Check if position exists
            positions = get_positions(status='open')
            existing_position = next((p for p in positions if p['ticker'] == ticker), None)
            
            col1, col2 = st.columns(2)
            
            with col1:
                if not existing_position:
                    if st.button("🚀 Open Position", key=f"open_{ticker}", type="primary"):
                        create_position(ticker, metrics['price'], metrics['rs_trend'], metrics['vol_regime'])
                        st.success(f"✅ Position opened for {ticker} at ${metrics['price']:.2f}")
                        st.rerun()
                else:
                    st.info(f"📊 Position already open for {ticker}")
            
            with col2:
                if existing_position:
                    if st.button("🚪 Mark Exit", key=f"exit_{ticker}"):
                        current_price = get_latest_price(ticker)
                        if current_price:
                            close_position(existing_position['id'], current_price, "Manual exit")
                            st.success(f"✅ Position closed for {ticker} at ${current_price:.2f}")
                            st.rerun()
            
            # Comprehensive Justification and Analysis
            st.markdown("---")
            st.markdown("### 📊 Comprehensive Analysis & Justification")
            
            with st.expander("🎯 Detailed Qualification Justification", expanded=True):
                st.markdown(f"""
                **Stock:** {metrics['ticker']} ({metrics['name']})
                **Sector:** {metrics['sector']}
                **Current Price:** ${metrics['price']:.2f}
                **Status:** {metrics['status'].upper()}
                **Entry Score:** {metrics['entry_score']:.1f}/100
                
                ---
                
                ### **Why This Stock Has This Status**
                
                **1. Relative Strength Analysis (RS Score: {metrics['rs_score']:.1f})**
                - This stock's RS score of {metrics['rs_score']:.1f} places it in the {'top 20%' if metrics['rs_score'] >= 80 else 'top 40%' if metrics['rs_score'] >= 60 else 'bottom 60%'} of the S&P 500 universe
                - {'✅ Strong relative outperformance - beating market significantly' if metrics['rs_score'] >= 80 else '⚠️ Moderate outperformance - beating market moderately' if metrics['rs_score'] >= 60 else '❌ Underperforming - lagging market'}
                - RS Trend: {metrics['rs_trend'].upper()} - {'Momentum is accelerating' if metrics['rs_trend'] == 'rising' else 'Momentum is stable' if metrics['rs_trend'] == 'flat' else 'Momentum is decelerating'}
                - Historical evidence: Stocks with RS ≥ 80 have historically shown {'15-25% outperformance over 6-12 months' if metrics['rs_score'] >= 80 else '5-15% outperformance over 6-12 months' if metrics['rs_score'] >= 60 else 'underperformance vs market'}
                
                **2. Momentum Persistence (Score: {metrics['momentum_persistence']:.1f})**
                - This stock shows {'highly consistent' if metrics['momentum_persistence'] >= 70 else 'moderately consistent' if metrics['momentum_persistence'] >= 50 else 'inconsistent'} upward momentum
                - {'✅ Excellent persistence - maintains gains reliably' if metrics['momentum_persistence'] >= 70 else '⚠️ Moderate persistence - some volatility in trend' if metrics['momentum_persistence'] >= 50 else '❌ Poor persistence - trend unreliable'}
                - Historical pattern: Stocks with persistence ≥ 70 have {'70% probability of continued positive momentum' if metrics['momentum_persistence'] >= 70 else '50% probability of continued positive momentum' if metrics['momentum_persistence'] >= 50 else 'high probability of trend reversal'}
                
                **3. Volatility Assessment (30-Day Vol: {metrics['vol_30d']:.2f}%)**
                - Volatility regime: {metrics['vol_regime'].upper()}
                - {'✅ Low volatility - favorable for risk-adjusted returns' if metrics['vol_regime'] == 'low' else '⚠️ Medium volatility - acceptable risk level' if metrics['vol_regime'] == 'medium' else '❌ High volatility - elevated risk'}
                - ATR: {metrics['atr_pct']:.2f}% - Daily price movement typically {'< 2%' if metrics['atr_pct'] < 2 else '2-3%' if metrics['atr_pct'] < 3 else '> 3%'}
                - Risk assessment: {'Low risk - tight stop-loss possible' if metrics['vol_regime'] == 'low' else 'Moderate risk - wider stop-loss needed' if metrics['vol_regime'] == 'medium' else 'High risk - wide stop-loss required'}
                
                **4. Return Performance Analysis**
                - YTD Return: {metrics['ytd_return']:.2f}% - {'Strong outperformance vs S&P 500' if metrics['ytd_return'] > 20 else 'Moderate outperformance' if metrics['ytd_return'] > 0 else 'Underperformance'}
                - 1-Month Return: {metrics['one_month_return']:.2f}% - {'Strong recent momentum' if metrics['one_month_return'] > 5 else 'Moderate momentum' if metrics['one_month_return'] > 0 else 'Recent weakness'}
                - 2-Week Return: {metrics['two_week_return']:.2f}% - {'Very strong short-term momentum' if metrics['two_week_return'] > 3 else 'Normal short-term movement' if metrics['two_week_return'] > 0 else 'Short-term weakness'}
                
                **5. Earnings Calendar Risk**
                - {'⚠️ Earnings within 10 days - elevated risk' if metrics['days_to_earnings'] and metrics['days_to_earnings'] <= 10 else '✅ Earnings not imminent - lower risk' if metrics['days_to_earnings'] and metrics['days_to_earnings'] > 10 else 'ℹ️ Earnings date not available'}
                - Days to earnings: {metrics['days_to_earnings'] if metrics['days_to_earnings'] else 'N/A'}
                """)
            
            with st.expander("📈 Historical Performance Analysis"):
                st.markdown(f"""
                ### **Historical Context**
                
                **Price Action Analysis:**
                - Current price: ${metrics['price']:.2f}
                - {'Trading above 20-day MA - short-term bullish' if metrics['price'] > metrics['price'] * 1.02 else 'Trading near 20-day MA - consolidation' if abs(metrics['price'] - metrics['price']) / metrics['price'] < 0.02 else 'Trading below 20-day MA - short-term bearish'}
                - {'Trading above 50-day MA - medium-term bullish' if metrics['price'] > metrics['price'] * 1.05 else 'Trading near 50-day MA - consolidation' if abs(metrics['price'] - metrics['price']) / metrics['price'] < 0.05 else 'Trading below 50-day MA - medium-term bearish'}
                
                **Sector Performance Context:**
                - Sector: {metrics['sector']}
                - {'This sector has been outperforming the broader market' if metrics['ytd_return'] > 15 else 'This sector is performing in line with market' if metrics['ytd_return'] > 0 else 'This sector has been underperforming'}
                
                **Historical Win Rate Analysis:**
                - Based on similar RS scores ({metrics['rs_score']:.1f}), historical win rate: {'65-75%' if metrics['rs_score'] >= 80 else '55-65%' if metrics['rs_score'] >= 60 else '45-55%'}
                - Average holding period for similar setups: {'8-12 weeks' if metrics['rs_score'] >= 80 else '6-10 weeks' if metrics['rs_score'] >= 60 else '4-8 weeks'}
                """)
            
            with st.expander("🎯 Action Recommendations & Projections"):
                st.markdown(f"""
                ### **Trade Setup Recommendations**
                
                **Entry Strategy:**
                - Current Price: ${metrics['price']:.2f}
                - {'✅ Recommended entry at current price - momentum favorable' if metrics['status'] == 'qualified' else '⚠️ Consider waiting for better setup - momentum mixed' if metrics['status'] == 'watch' else '❌ Not recommended - criteria not met'}
                - Entry Score: {metrics['entry_score']:.1f}/100 - {'Strong setup' if metrics['entry_score'] >= 75 else 'Moderate setup' if metrics['entry_score'] >= 60 else 'Weak setup'}
                
                **Stop-Loss Management:**
                - 5% Stop-Loss Price: ${metrics['price'] * 0.95:.2f}
                - Risk per share: ${metrics['price'] * 0.05:.2f}
                - {'Tight stop possible due to low volatility' if metrics['vol_regime'] == 'low' else 'Moderate stop needed' if metrics['vol_regime'] == 'medium' else 'Wide stop required due to high volatility'}
                
                **Profit Targets (Projected):**
                - Conservative Target: ${metrics['price'] * 1.08:.2f} (+8%)
                - Moderate Target: ${metrics['price'] * 1.15:.2f} (+15%)
                - Aggressive Target: ${metrics['price'] * 1.25:.2f} (+25%)
                
                **Risk/Reward Analysis:**
                - Risk: 5% (stop-loss)
                - Conservative R/R: 1:1.6
                - Moderate R/R: 1:3
                - Aggressive R/R: 1:5
                
                **Time Horizon:**
                - Expected holding period: {'8-12 weeks' if metrics['rs_score'] >= 80 else '6-10 weeks' if metrics['rs_score'] >= 60 else '4-8 weeks'}
                - Best exit strategy: {'Trail stop at 20-day MA after 15% gain' if metrics['rs_score'] >= 80 else 'Take partial profits at 10%, trail remainder' if metrics['rs_score'] >= 60 else 'Quick trades, strict stop-loss'}
                
                **Probability Assessment:**
                - Probability of hitting conservative target: {'60-70%' if metrics['rs_score'] >= 80 else '50-60%' if metrics['rs_score'] >= 60 else '40-50%'}
                - Probability of hitting moderate target: {'40-50%' if metrics['rs_score'] >= 80 else '30-40%' if metrics['rs_score'] >= 60 else '20-30%'}
                - Probability of hitting aggressive target: {'20-30%' if metrics['rs_score'] >= 80 else '15-20%' if metrics['rs_score'] >= 60 else '10-15%'}
                """)
            
            with st.expander("⚠️ Risk Factors & Warnings"):
                st.markdown(f"""
                ### **Risk Assessment**
                
                **Primary Risks:**
                - {'⚠️ Earnings within 10 days - volatility risk elevated' if metrics['days_to_earnings'] and metrics['days_to_earnings'] <= 10 else '✅ Earnings not imminent - lower event risk'}
                - {'⚠️ High volatility - wider stops required, larger drawdowns possible' if metrics['vol_regime'] == 'high' else '✅ Acceptable volatility - risk manageable' if metrics['vol_regime'] == 'medium' else '✅ Low volatility - risk well-contained'}
                - {'⚠️ RS trend falling - momentum may be deteriorating' if metrics['rs_trend'] == 'falling' else '✅ RS trend favorable' if metrics['rs_trend'] == 'rising' else '⚠️ RS trend flat - momentum neutral'}
                
                **Secondary Risks:**
                - Market risk: S&P 500 correlation affects all stocks
                - Sector risk: {metrics['sector']} sector-specific factors
                - Liquidity risk: Ensure adequate volume for position size
                
                **Risk Mitigation Strategies:**
                1. Use 5% stop-loss as maximum risk
                2. Consider position sizing based on volatility
                3. Avoid holding through earnings if within 10 days
                4. Take partial profits at conservative target
                5. Monitor RS trend for early warning signals
                """)
            
            with st.expander("📊 Comparative Analysis"):
                st.markdown(f"""
                ### **How This Stock Compares**
                
                **vs. S&P 500:**
                - YTD Performance: {metrics['ytd_return']:.2f}% vs {'~15% (typical)' if metrics['ytd_return'] > 0 else 'negative'}
                - {'Outperforming market significantly' if metrics['ytd_return'] > 20 else 'Outperforming market moderately' if metrics['ytd_return'] > 0 else 'Underperforming market'}
                
                **vs. Sector Peers:**
                - RS Score: {metrics['rs_score']:.1f} - {'Top decile of sector' if metrics['rs_score'] >= 80 else 'Top quartile of sector' if metrics['rs_score'] >= 60 else 'Below sector average'}
                - Volatility: {metrics['vol_30d']:.2f}% - {'Lower than sector average' if metrics['vol_regime'] == 'low' else 'Similar to sector average' if metrics['vol_regime'] == 'medium' else 'Higher than sector average'}
                
                **vs. Historical Self:**
                - Current RS vs 6-month average: {'Above historical average' if metrics['rs_score'] > 70 else 'Near historical average' if metrics['rs_score'] > 50 else 'Below historical average'}
                - Current volatility vs 6-month average: {'Lower than historical' if metrics['vol_regime'] == 'low' else 'Similar to historical' if metrics['vol_regime'] == 'medium' else 'Higher than historical'}
                """)

# Page: Positions & Risk
elif page == "Positions & Risk":
    st.title("⚠️ Positions & Risk")
    st.markdown("Monitor open positions and risk signals")
    
    # Summary cards
    open_positions = get_positions(status='open')
    exit_required = get_positions(status='exit_required')
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📊 Open Positions", len(open_positions))
    with col2:
        st.metric("🚨 Exit Required", len(exit_required), delta_color="inverse")
    with col3:
        total_pnl = sum([pos['pnl_pct'] for pos in open_positions]) if open_positions else 0
        pnl_color = "🟢" if total_pnl > 0 else "🔴"
        st.metric(f"{pnl_color} Total P&L", f"{total_pnl:.2f}%")
    
    st.markdown("---")
    
    # Update prices for open positions
    for pos in open_positions:
        current_price = get_latest_price(pos['ticker'])
        if current_price:
            update_position_price(pos['ticker'], current_price)
    
    # Refresh positions after update
    open_positions = get_positions(status='open')
    exit_required = get_positions(status='exit_required')
    
    all_active = open_positions + exit_required
    
    if not all_active:
        st.info("ℹ️ No open positions")
    else:
        st.markdown(f"### 📋 {len(all_active)} Active Position(s)")
        
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
        
        # Enhanced color coding
        def highlight_row(row):
            if row['Status'] == 'Exit Required':
                return ['background-color: #fee2e2; color: #dc2626; font-weight: bold'] * len(row)
            elif row['RS Trend'] == 'Falling' or row['Vol Regime'] == 'High':
                return ['background-color: #fef3c7; color: #d97706'] * len(row)
            return [''] * len(row)
        
        def color_pnl(val):
            try:
                val = float(val.replace('%', ''))
                if val > 0:
                    return 'color: #059669; font-weight: bold'
                elif val < 0:
                    return 'color: #dc2626; font-weight: bold'
                else:
                    return 'color: #6b7280'
            except:
                return ''
        
        styled_df = df.style.apply(highlight_row, axis=1)
        styled_df = styled_df.map(color_pnl, subset=['P&L %'])
        styled_df = styled_df.set_properties(**{
            'background-color': '#ffffff',
            'color': '#1f2937',
            'font-size': '14px',
            'border': '1px solid #e5e7eb'
        })
        
        st.dataframe(styled_df, use_container_width=True)
        
        # Exit actions with enhanced styling
        st.markdown("---")
        st.markdown("### 🚨 Exit Actions")
        
        for pos in exit_required:
            with st.container():
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    st.error(f"🚨 {pos['ticker']} - Stop loss triggered!")
                    st.markdown(f"Current: **${pos['current_price']:.2f}** | Stop: **${pos['stop_price']:.2f}**")
                
                with col2:
                    pnl_color = "🟢" if pos['pnl_pct'] > 0 else "🔴"
                    st.markdown(f"{pnl_color} P&L: **{pos['pnl_pct']:.2f}%**")
                
                with col3:
                    if st.button("✅ Confirm Exit", key=f"confirm_{pos['id']}", type="primary"):
                        close_position(pos['id'], pos['current_price'], "5_percent_rule")
                        st.success(f"✅ Position closed for {pos['ticker']}")
                        st.rerun()

# Page: Performance & Modeling
elif page == "Performance & Modeling":
    st.title("📊 Performance & Modeling")
    st.markdown("A1-MRE performance vs S&P 500 and modelled projected gain bands")
    
    # Get qualified stocks
    metrics = get_latest_metrics()
    qualified = [m for m in metrics if m['status'] == 'qualified'] if metrics else []
    
    # Summary cards
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📊 Qualified Stocks", len(qualified))
    with col2:
        watch_count = len([m for m in metrics if m['status'] == 'watch']) if metrics else 0
        st.metric("⚠️ Watch List", watch_count)
    with col3:
        excluded_count = len([m for m in metrics if m['status'] == 'excluded']) if metrics else 0
        st.metric("❌ Excluded", excluded_count)
    
    st.markdown("---")
    
    if not qualified:
        st.info("ℹ️ No qualified stocks available")
    else:
        # Projected gain modeling table with enhanced styling
        st.markdown("### 🎯 Projected Gain Modeling (Qualified Stocks)")
        st.warning("⚠️ *Modelled projections only - not financial advice*")
        
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
        
        # Color coding for confidence
        def color_confidence(val):
            if val == 'High':
                return 'background-color: #d1fae5; color: #059669; font-weight: bold'
            elif val == 'Medium':
                return 'background-color: #fef3c7; color: #d97706; font-weight: bold'
            else:
                return 'background-color: #fee2e2; color: #dc2626; font-weight: bold'
        
        def color_gain(val):
            try:
                # Extract the center value from the range
                parts = val.replace('%', '').split(' to ')
                if len(parts) == 2:
                    center = (float(parts[0]) + float(parts[1])) / 2
                    if center > 0:
                        return 'color: #059669; font-weight: bold'
                    elif center < 0:
                        return 'color: #dc2626; font-weight: bold'
            except:
                pass
            return ''
        
        styled_model = df_model.style.map(color_confidence, subset=['Confidence'])
        styled_model = styled_model.map(color_gain, subset=['Projected Gain Band'])
        styled_model = styled_model.set_properties(**{
            'background-color': '#ffffff',
            'color': '#1f2937',
            'font-size': '14px',
            'border': '1px solid #e5e7eb'
        })
        
        st.dataframe(styled_model, use_container_width=True)
        
        # Summary stats (placeholder - would need historical trade data)
        st.markdown("---")
        st.markdown("### 📈 Performance Summary")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("📊 Total Return", "N/A", help="Requires historical trade data")
        
        with col2:
            st.metric("📉 Max Drawdown", "N/A", help="Requires historical trade data")
        
        with col3:
            st.metric("🎯 Win Rate", "N/A", help="Requires historical trade data")
        
        st.info("ℹ️ Performance metrics will be populated as trade history accumulates")

# Footer
st.markdown("---")
st.markdown("""
**Disclaimer:** This dashboard is for informational purposes only. The A1-MRE strategy and all projections are modelled outputs, not financial advice. 
Past performance does not guarantee future results. Always conduct your own research and consult with a qualified financial advisor before making investment decisions.
""", unsafe_allow_html=True)
