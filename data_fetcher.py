import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Tuple, Dict
import time
import requests

def get_sp500_tickers() -> List[Tuple[str, str, str]]:
    """
    Fetch S&P 500 tickers from Wikipedia with fallback to sample data.
    Returns list of (ticker, name, sector) tuples.
    """
    # For testing, use sample data to avoid yfinance API issues
    print("Using sample ticker data for testing...")
    return get_sample_tickers()
    
    # Uncomment below to try Wikipedia fetch (currently disabled due to yfinance issues)
    # try:
    #     # Try with headers to avoid 403
    #     headers = {
    #         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    #     }
    #     url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    #     response = requests.get(url, headers=headers, timeout=10)
    #     tables = pd.read_html(response.text)
    #     sp500_table = tables[0]
    #     
    #     ticker_data = []
    #     for _, row in sp500_table.iterrows():
    #         ticker = row['Symbol'].replace('.', '-')  # yfinance uses '-' for dots
    #         name = row['Security']
    #         sector = row['GICS Sector']
    #         ticker_data.append((ticker, name, sector))
    #     
    #     return ticker_data
    # except Exception as e:
    #     print(f"Error fetching S&P 500 tickers from Wikipedia: {e}")
    #     print("Using fallback sample data for testing...")
    #     return get_sample_tickers()

def get_sample_tickers() -> List[Tuple[str, str, str]]:
    """Return a sample of major S&P 500 stocks for testing."""
    return [
        ('AAPL', 'Apple Inc.', 'Technology'),
        ('MSFT', 'Microsoft Corporation', 'Technology'),
        ('GOOGL', 'Alphabet Inc.', 'Technology'),
        ('AMZN', 'Amazon.com Inc.', 'Consumer Cyclical'),
        ('NVDA', 'NVIDIA Corporation', 'Technology'),
        ('META', 'Meta Platforms Inc.', 'Technology'),
        ('TSLA', 'Tesla Inc.', 'Consumer Cyclical'),
        ('JPM', 'JPMorgan Chase & Co.', 'Financials'),
        ('V', 'Visa Inc.', 'Financials'),
        ('JNJ', 'Johnson & Johnson', 'Healthcare'),
        ('WMT', 'Walmart Inc.', 'Consumer Defensive'),
        ('PG', 'Procter & Gamble Co.', 'Consumer Defensive'),
        ('XOM', 'Exxon Mobil Corp.', 'Energy'),
        ('CVX', 'Chevron Corporation', 'Energy'),
        ('LLY', 'Eli Lilly and Co.', 'Healthcare'),
        ('ABBV', 'AbbVie Inc.', 'Healthcare'),
        ('MRK', 'Merck & Co. Inc.', 'Healthcare'),
        ('AVGO', 'Broadcom Inc.', 'Technology'),
        ('PEP', 'PepsiCo Inc.', 'Consumer Defensive'),
        ('COST', 'Costco Wholesale Corp.', 'Consumer Defensive'),
    ]

def get_price_data(ticker: str, period: str = "1y") -> pd.DataFrame:
    """
    Fetch historical price data for a ticker.
    period: "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"
    """
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period=period)
        return data
    except Exception as e:
        print(f"Error fetching price data for {ticker}: {e}")
        return pd.DataFrame()

def get_latest_price(ticker: str) -> float:
    """Get the latest closing price for a ticker."""
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period="5d")
        if not data.empty:
            return data['Close'].iloc[-1]
        return None
    except Exception as e:
        print(f"Error fetching latest price for {ticker}: {e}")
        return None

def get_earnings_date(ticker: str) -> datetime:
    """Get next earnings date for a ticker."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        if 'nextEarningsDate' in info and info['nextEarningsDate']:
            return pd.to_datetime(info['nextEarningsDate'])
        return None
    except Exception as e:
        print(f"Error fetching earnings date for {ticker}: {e}")
        return None

def batch_get_prices(tickers: List[str], period: str = "1y") -> Dict[str, pd.DataFrame]:
    """
    Fetch price data for multiple tickers in batches to avoid rate limits.
    """
    price_data = {}
    batch_size = 50
    
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        for ticker in batch:
            data = get_price_data(ticker, period)
            if not data.empty:
                price_data[ticker] = data
            time.sleep(0.1)  # Small delay to avoid rate limits
    
    return price_data

def batch_get_latest_prices(tickers: List[str]) -> Dict[str, float]:
    """Get latest prices for multiple tickers."""
    prices = {}
    for ticker in tickers:
        price = get_latest_price(ticker)
        if price:
            prices[ticker] = price
        time.sleep(0.05)  # Small delay
    return prices

def get_sp500_index_data(period: str = "1y") -> pd.DataFrame:
    """Get S&P 500 index data (^GSPC)."""
    return get_price_data("^GSPC", period)
