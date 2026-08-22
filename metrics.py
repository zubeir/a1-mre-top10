import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List
from data_fetcher import get_price_data, get_latest_price, get_earnings_date

def calculate_returns(price_data: pd.DataFrame) -> Dict[str, float]:
    """Calculate YTD, 1-month, and 2-week returns."""
    if price_data.empty or len(price_data) < 30:
        return {'ytd_return': 0, 'one_month_return': 0, 'two_week_return': 0}
    
    current_price = price_data['Close'].iloc[-1]
    
    # YTD return
    start_of_year = price_data.index[0].replace(month=1, day=1)
    ytd_data = price_data[price_data.index >= start_of_year]
    if not ytd_data.empty:
        ytd_return = ((current_price - ytd_data['Close'].iloc[0]) / ytd_data['Close'].iloc[0]) * 100
    else:
        ytd_return = 0
    
    # 1-month return (30 trading days)
    if len(price_data) >= 30:
        one_month_return = ((current_price - price_data['Close'].iloc[-30]) / price_data['Close'].iloc[-30]) * 100
    else:
        one_month_return = 0
    
    # 2-week return (10 trading days)
    if len(price_data) >= 10:
        two_week_return = ((current_price - price_data['Close'].iloc[-10]) / price_data['Close'].iloc[-10]) * 100
    else:
        two_week_return = 0
    
    return {
        'ytd_return': ytd_return,
        'one_month_return': one_month_return,
        'two_week_return': two_week_return
    }

def calculate_momentum_persistence(returns_dict: Dict[str, float], universe_returns: List[Dict[str, float]]) -> float:
    """
    Calculate momentum persistence (0-100) based on percentile ranks of returns.
    """
    if not universe_returns:
        return 50
    
    # Extract returns for this ticker
    ytd = returns_dict['ytd_return']
    one_month = returns_dict['one_month_return']
    two_week = returns_dict['two_week_return']
    
    # Calculate percentile ranks
    ytd_values = [r['ytd_return'] for r in universe_returns]
    one_month_values = [r['one_month_return'] for r in universe_returns]
    two_week_values = [r['two_week_return'] for r in universe_returns]
    
    rank_ytd = pd.Series(ytd_values).rank(pct=True).iloc[-1] * 100 if ytd_values else 50
    rank_1m = pd.Series(one_month_values).rank(pct=True).iloc[-1] * 100 if one_month_values else 50
    rank_2w = pd.Series(two_week_values).rank(pct=True).iloc[-1] * 100 if two_week_values else 50
    
    # Use actual percentile of this ticker's values
    rank_ytd = (pd.Series(ytd_values + [ytd]).rank(pct=True).iloc[-1]) * 100
    rank_1m = (pd.Series(one_month_values + [one_month]).rank(pct=True).iloc[-1]) * 100
    rank_2w = (pd.Series(two_week_values + [two_week]).rank(pct=True).iloc[-1]) * 100
    
    persistence = (rank_ytd + rank_1m + rank_2w) / 3
    return persistence

def calculate_rs_score(price_data: pd.DataFrame, universe_6m_returns: List[float]) -> tuple:
    """
    Calculate Relative Strength (RS) score (0-100) based on 6-month return percentile.
    Returns (rs_score, rs_trend).
    """
    if price_data.empty or len(price_data) < 126:  # ~6 months of trading days
        return 50, 'flat'
    
    current_price = price_data['Close'].iloc[-1]
    price_6m_ago = price_data['Close'].iloc[-126] if len(price_data) >= 126 else price_data['Close'].iloc[0]
    six_month_return = ((current_price - price_6m_ago) / price_6m_ago) * 100
    
    # Calculate percentile rank vs universe
    if universe_6m_returns:
        rs_score = (pd.Series(universe_6m_returns + [six_month_return]).rank(pct=True).iloc[-1]) * 100
    else:
        rs_score = 50
    
    # Determine RS trend by comparing recent RS values
    if len(price_data) >= 20:
        # Calculate RS over different periods
        recent_10d_return = ((current_price - price_data['Close'].iloc[-10]) / price_data['Close'].iloc[-10]) * 100
        prior_10d_return = ((price_data['Close'].iloc[-10] - price_data['Close'].iloc[-20]) / price_data['Close'].iloc[-20]) * 100
        
        if recent_10d_return > prior_10d_return * 1.05:
            rs_trend = 'rising'
        elif recent_10d_return < prior_10d_return * 0.95:
            rs_trend = 'falling'
        else:
            rs_trend = 'flat'
    else:
        rs_trend = 'flat'
    
    return rs_score, rs_trend

def calculate_volatility_metrics(price_data: pd.DataFrame) -> Dict[str, float]:
    """
    Calculate 30-day volatility, ATR %, and volatility regime.
    """
    if price_data.empty or len(price_data) < 30:
        return {'vol_30d': 0, 'atr_pct': 0, 'vol_regime': 'medium'}
    
    # 30-day volatility (standard deviation of daily returns)
    daily_returns = price_data['Close'].pct_change().dropna()
    if len(daily_returns) >= 30:
        vol_30d = daily_returns.tail(30).std() * np.sqrt(252) * 100  # Annualized
    else:
        vol_30d = daily_returns.std() * np.sqrt(252) * 100 if len(daily_returns) > 0 else 0
    
    # ATR (Average True Range) over 14 days
    high = price_data['High']
    low = price_data['Low']
    close = price_data['Close']
    
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=14).mean().iloc[-1]
    
    current_price = price_data['Close'].iloc[-1]
    atr_pct = (atr / current_price) * 100 if current_price > 0 else 0
    
    return {
        'vol_30d': vol_30d,
        'atr_pct': atr_pct
    }

def determine_vol_regime(vol_30d: float, universe_volatilities: List[float]) -> str:
    """Determine volatility regime based on universe distribution."""
    if not universe_volatilities:
        return 'medium'
    
    median_vol = np.median(universe_volatilities)
    percentile_75 = np.percentile(universe_volatilities, 75)
    
    if vol_30d < median_vol:
        return 'low'
    elif vol_30d < percentile_75:
        return 'medium'
    else:
        return 'high'

def calculate_entry_score(rs_score: float, momentum_persistence: float, 
                          vol_regime: str, rs_trend: str, days_to_earnings: int = None) -> float:
    """
    Calculate composite Entry Score (0-100).
    Weights: RS=0.3, Persistence=0.3, Volatility=0.15, Trend=0.15, Earnings=0.10
    """
    # Volatility factor
    vol_factor = {'low': 100, 'medium': 80, 'high': 50}.get(vol_regime, 80)
    
    # Trend factor
    trend_factor = {'rising': 100, 'flat': 70, 'falling': 40}.get(rs_trend, 70)
    
    # Earnings factor
    if days_to_earnings is None:
        earnings_factor = 100  # Assume safe if unknown
    elif days_to_earnings > 10:
        earnings_factor = 100
    else:
        earnings_factor = 40
    
    # Calculate weighted score
    entry_score = (
        0.3 * rs_score +
        0.3 * momentum_persistence +
        0.15 * vol_factor +
        0.15 * trend_factor +
        0.10 * earnings_factor
    )
    
    return min(100, max(0, entry_score))

def determine_status(rs_score: float, momentum_persistence: float, 
                     vol_regime: str, days_to_earnings: int, entry_score: float) -> str:
    """
    Determine status: qualified, watch, or excluded.
    """
    if (rs_score >= 80 and 
        momentum_persistence >= 70 and 
        vol_regime in ['low', 'medium'] and 
        (days_to_earnings is None or days_to_earnings > 10) and 
        entry_score >= 75):
        return 'qualified'
    elif rs_score >= 60:
        return 'watch'
    else:
        return 'excluded'

def compute_all_metrics(ticker: str, price_data: pd.DataFrame, 
                       universe_metrics: List[Dict]) -> Dict:
    """
    Compute all metrics for a single ticker.
    """
    current_price = price_data['Close'].iloc[-1] if not price_data.empty else 0
    
    # Calculate returns
    returns = calculate_returns(price_data)
    
    # Calculate momentum persistence
    universe_returns = [{'ytd_return': m.get('ytd_return', 0), 
                        'one_month_return': m.get('one_month_return', 0),
                        'two_week_return': m.get('two_week_return', 0)} 
                       for m in universe_metrics]
    momentum_persistence = calculate_momentum_persistence(returns, universe_returns)
    
    # Calculate RS
    universe_6m_returns = [m.get('six_month_return', 0) for m in universe_metrics]
    # Need to compute 6m return for universe first
    rs_score, rs_trend = calculate_rs_score(price_data, universe_6m_returns)
    
    # Calculate volatility
    vol_metrics = calculate_volatility_metrics(price_data)
    universe_volatilities = [m.get('vol_30d', 0) for m in universe_metrics]
    vol_regime = determine_vol_regime(vol_metrics['vol_30d'], universe_volatilities)
    
    # Get earnings date
    earnings_date = get_earnings_date(ticker)
    days_to_earnings = None
    if earnings_date:
        days_to_earnings = (earnings_date - datetime.now()).days
    
    # Calculate entry score
    entry_score = calculate_entry_score(rs_score, momentum_persistence, vol_regime, 
                                        rs_trend, days_to_earnings)
    
    # Determine status
    status = determine_status(rs_score, momentum_persistence, vol_regime, 
                            days_to_earnings, entry_score)
    
    return {
        'date': datetime.now().date(),
        'ticker': ticker,
        'price': current_price,
        'ytd_return': returns['ytd_return'],
        'one_month_return': returns['one_month_return'],
        'two_week_return': returns['two_week_return'],
        'momentum_persistence': momentum_persistence,
        'rs_score': rs_score,
        'rs_trend': rs_trend,
        'vol_30d': vol_metrics['vol_30d'],
        'atr_pct': vol_metrics['atr_pct'],
        'vol_regime': vol_regime,
        'earnings_date': earnings_date.date() if earnings_date else None,
        'days_to_earnings': days_to_earnings,
        'entry_score': entry_score,
        'status': status,
        'six_month_return': ((current_price - price_data['Close'].iloc[-126]) / price_data['Close'].iloc[-126]) * 100 
                           if len(price_data) >= 126 else 0
    }

def compute_projected_gain(persistence: float, vol_regime: str, rs_trend: str) -> Dict[str, float]:
    """
    Compute projected gain band (non-predictive model).
    Returns dict with center, lower, upper bounds and confidence level.
    """
    # Normalize persistence
    persistence_norm = persistence / 100
    
    # Volatility factor
    vol_factor = {'low': 1.0, 'medium': 0.8, 'high': 0.6}.get(vol_regime, 0.8)
    
    # Trend factor
    trend_factor = {'rising': 1.0, 'flat': 0.8, 'falling': 0.6}.get(rs_trend, 0.8)
    
    # Calculate center
    center = persistence_norm * vol_factor * trend_factor * 10  # Scale to reasonable %
    
    # Band width (2-3%)
    band_width = 2.5
    
    lower = center - band_width
    upper = center + band_width
    
    # Confidence level
    if persistence >= 80 and rs_trend == 'rising' and vol_regime == 'low':
        confidence = 'High'
    elif persistence >= 70 and rs_trend in ['rising', 'flat'] and vol_regime in ['low', 'medium']:
        confidence = 'Medium'
    else:
        confidence = 'Low'
    
    return {
        'center': center,
        'lower': lower,
        'upper': upper,
        'confidence': confidence
    }
