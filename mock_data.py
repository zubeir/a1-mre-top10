"""
Mock data generator for testing when yfinance API is unavailable.
Generates realistic price history and metrics for sample tickers.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict
import random

def generate_mock_price_data(ticker: str, days: int = 252) -> pd.DataFrame:
    """Generate mock price data for a ticker."""
    # Set random seed based on ticker for consistency
    seed = sum(ord(c) for c in ticker)
    np.random.seed(seed)
    
    # Generate dates
    end_date = datetime.now()
    dates = pd.date_range(end=end_date, periods=days, freq='B')  # Business days
    
    # Starting price based on ticker (some realistic base prices)
    base_prices = {
        'AAPL': 180, 'MSFT': 380, 'GOOGL': 140, 'AMZN': 180, 'NVDA': 480,
        'META': 500, 'TSLA': 240, 'JPM': 195, 'V': 280, 'JNJ': 160,
        'WMT': 165, 'PG': 160, 'XOM': 110, 'CVX': 155, 'LLY': 580,
        'ABBV': 175, 'MRK': 110, 'AVGO': 1300, 'PEP': 170, 'COST': 560
    }
    
    base_price = base_prices.get(ticker, 100)
    
    # Generate price path with random walk
    returns = np.random.normal(0.0005, 0.02, days)  # Daily returns
    prices = [base_price]
    
    for ret in returns[1:]:
        new_price = prices[-1] * (1 + ret)
        prices.append(max(new_price, 1))  # Ensure positive price
    
    # Create OHLC data
    df = pd.DataFrame({
        'Open': [p * (1 + np.random.uniform(-0.01, 0.01)) for p in prices],
        'High': [p * (1 + np.random.uniform(0, 0.02)) for p in prices],
        'Low': [p * (1 - np.random.uniform(0, 0.02)) for p in prices],
        'Close': prices,
        'Volume': [int(np.random.uniform(1000000, 50000000)) for _ in range(days)]
    }, index=dates)
    
    # Ensure High >= Close >= Low
    df['High'] = df[['High', 'Close']].max(axis=1)
    df['Low'] = df[['Low', 'Close']].min(axis=1)
    
    return df

def generate_mock_metrics(ticker: str) -> Dict:
    """Generate mock metrics for a ticker."""
    seed = sum(ord(c) for c in ticker)
    np.random.seed(seed)
    
    # Generate realistic metrics
    rs_score = np.random.uniform(40, 95)
    momentum_persistence = np.random.uniform(30, 90)
    vol_30d = np.random.uniform(15, 45)
    
    # Determine volatility regime
    if vol_30d < 25:
        vol_regime = 'low'
    elif vol_30d < 35:
        vol_regime = 'medium'
    else:
        vol_regime = 'high'
    
    # RS trend
    rs_trend = random.choice(['rising', 'flat', 'falling'])
    
    # Returns
    ytd_return = np.random.uniform(-20, 60)
    one_month_return = np.random.uniform(-15, 20)
    two_week_return = np.random.uniform(-10, 15)
    
    # ATR
    atr_pct = vol_30d * np.random.uniform(0.5, 1.5)
    
    # Entry score calculation
    vol_factor = {'low': 100, 'medium': 80, 'high': 50}.get(vol_regime, 80)
    trend_factor = {'rising': 100, 'flat': 70, 'falling': 40}.get(rs_trend, 70)
    earnings_factor = 100  # Assume safe
    
    entry_score = (
        0.3 * rs_score +
        0.3 * momentum_persistence +
        0.15 * vol_factor +
        0.15 * trend_factor +
        0.10 * earnings_factor
    )
    
    # Status
    if (rs_score >= 80 and 
        momentum_persistence >= 70 and 
        vol_regime in ['low', 'medium'] and 
        entry_score >= 75):
        status = 'qualified'
    elif rs_score >= 60:
        status = 'watch'
    else:
        status = 'excluded'
    
    # Get current price from mock data
    price_data = generate_mock_price_data(ticker)
    current_price = price_data['Close'].iloc[-1]
    
    return {
        'date': datetime.now().date(),
        'ticker': ticker,
        'price': current_price,
        'ytd_return': ytd_return,
        'one_month_return': one_month_return,
        'two_week_return': two_week_return,
        'momentum_persistence': momentum_persistence,
        'rs_score': rs_score,
        'rs_trend': rs_trend,
        'vol_30d': vol_30d,
        'atr_pct': atr_pct,
        'vol_regime': vol_regime,
        'earnings_date': None,
        'days_to_earnings': None,
        'entry_score': entry_score,
        'status': status,
        'six_month_return': np.random.uniform(-30, 80)
    }

def generate_all_mock_metrics(tickers) -> list:
    """Generate mock metrics for all tickers."""
    metrics_list = []
    for ticker, name, sector in tickers:
        metrics = generate_mock_metrics(ticker)
        metrics['name'] = name
        metrics['sector'] = sector
        metrics_list.append(metrics)
    return metrics_list
