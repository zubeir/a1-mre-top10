"""
Data update script for A1-MRE Dashboard.
Fetches latest market data, computes metrics, and updates the database.
Run this daily after market close.
"""

import sys
from datetime import datetime
import time

sys.path.append('.')

from database import init_database, save_universe, save_metrics, log_event, get_sp500_universe
from data_fetcher import get_sp500_tickers, batch_get_prices
from metrics import compute_all_metrics
from mock_data import generate_all_mock_metrics

def update_daily_metrics():
    """Main function to update daily metrics for all S&P 500 stocks."""
    print(f"Starting daily metrics update: {datetime.now()}")
    
    # Initialize database
    init_database()
    
    # Fetch S&P 500 universe
    print("Fetching S&P 500 universe...")
    ticker_data = get_sp500_tickers()
    
    if not ticker_data:
        print("Error: Could not fetch S&P 500 tickers")
        return
    
    print(f"Found {len(ticker_data)} S&P 500 stocks")
    
    # Save universe to database
    save_universe(ticker_data)
    
    # Get tickers list
    tickers = [t[0] for t in ticker_data]
    
    # Try to fetch real price data, fall back to mock data
    print("Attempting to fetch real price data...")
    price_data_dict = batch_get_prices(tickers, period="1y")
    
    if len(price_data_dict) < len(tickers) * 0.5:  # If less than 50% success rate
        print("Insufficient real data available. Using mock data for testing...")
        all_metrics = generate_all_mock_metrics(ticker_data)
    else:
        print(f"Retrieved price data for {len(price_data_dict)} tickers")
        
        # First pass: compute basic metrics for universe comparison
        universe_metrics = []
        for ticker, price_data in price_data_dict.items():
            if not price_data.empty:
                try:
                    # Compute basic metrics for universe comparison
                    current_price = price_data['Close'].iloc[-1]
                    
                    # Calculate returns
                    if len(price_data) >= 30:
                        one_month_return = ((current_price - price_data['Close'].iloc[-30]) / price_data['Close'].iloc[-30]) * 100
                    else:
                        one_month_return = 0
                    
                    if len(price_data) >= 10:
                        two_week_return = ((current_price - price_data['Close'].iloc[-10]) / price_data['Close'].iloc[-10]) * 100
                    else:
                        two_week_return = 0
                    
                    # YTD
                    start_of_year = price_data.index[0].replace(month=1, day=1)
                    ytd_data = price_data[price_data.index >= start_of_year]
                    if not ytd_data.empty:
                        ytd_return = ((current_price - ytd_data['Close'].iloc[0]) / ytd_data['Close'].iloc[0]) * 100
                    else:
                        ytd_return = 0
                    
                    # 6-month return for RS
                    if len(price_data) >= 126:
                        six_month_return = ((current_price - price_data['Close'].iloc[-126]) / price_data['Close'].iloc[-126]) * 100
                    else:
                        six_month_return = 0
                    
                    # Volatility
                    daily_returns = price_data['Close'].pct_change().dropna()
                    if len(daily_returns) >= 30:
                        vol_30d = daily_returns.tail(30).std() * (252 ** 0.5) * 100
                    else:
                        vol_30d = daily_returns.std() * (252 ** 0.5) * 100 if len(daily_returns) > 0 else 0
                    
                    universe_metrics.append({
                        'ytd_return': ytd_return,
                        'one_month_return': one_month_return,
                        'two_week_return': two_week_return,
                        'six_month_return': six_month_return,
                        'vol_30d': vol_30d
                    })
                except Exception as e:
                    print(f"Error computing basic metrics for {ticker}: {e}")
                    continue
        
        print(f"Computed basic metrics for {len(universe_metrics)} tickers")
        
        # Second pass: compute full metrics with universe context
        all_metrics = []
        for ticker, price_data in price_data_dict.items():
            if not price_data.empty:
                try:
                    metrics = compute_all_metrics(ticker, price_data, universe_metrics)
                    all_metrics.append(metrics)
                    print(f"Computed metrics for {ticker}: Entry Score={metrics['entry_score']:.1f}, Status={metrics['status']}")
                    time.sleep(0.05)  # Small delay to avoid rate limits
                except Exception as e:
                    print(f"Error computing full metrics for {ticker}: {e}")
                    continue
    
    # Save metrics to database
    print(f"Saving {len(all_metrics)} metrics to database...")
    save_metrics(all_metrics)
    
    # Log the scan run
    log_event('scan_run', {
        'timestamp': datetime.now().isoformat(),
        'tickers_processed': len(all_metrics),
        'qualified_count': len([m for m in all_metrics if m['status'] == 'qualified']),
        'watch_count': len([m for m in all_metrics if m['status'] == 'watch']),
        'excluded_count': len([m for m in all_metrics if m['status'] == 'excluded'])
    })
    
    print("Daily metrics update completed successfully")
    print(f"Qualified: {len([m for m in all_metrics if m['status'] == 'qualified'])}")
    print(f"Watch: {len([m for m in all_metrics if m['status'] == 'watch'])}")
    print(f"Excluded: {len([m for m in all_metrics if m['status'] == 'excluded'])}")

if __name__ == "__main__":
    update_daily_metrics()
