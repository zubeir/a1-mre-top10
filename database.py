import sqlite3
from datetime import datetime
from pathlib import Path
import json

DB_PATH = Path(__file__).parent / "a1_mre.db"

def get_connection():
    """Get SQLite database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initialize database with all required tables."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Universe table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS universe (
            ticker TEXT PRIMARY KEY,
            name TEXT,
            sector TEXT,
            is_active BOOLEAN DEFAULT 1
        )
    """)
    
    # Metrics table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE,
            ticker TEXT,
            price REAL,
            ytd_return REAL,
            one_month_return REAL,
            two_week_return REAL,
            momentum_persistence REAL,
            rs_score REAL,
            rs_trend TEXT,
            vol_30d REAL,
            atr_pct REAL,
            vol_regime TEXT,
            earnings_date DATE,
            days_to_earnings INTEGER,
            entry_score REAL,
            status TEXT,
            FOREIGN KEY (ticker) REFERENCES universe(ticker),
            UNIQUE(date, ticker)
        )
    """)
    
    # Positions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT,
            entry_date DATE,
            entry_price REAL,
            stop_price REAL,
            current_price REAL,
            pnl_pct REAL,
            rs_trend TEXT,
            vol_regime TEXT,
            status TEXT,
            exit_date DATE,
            exit_price REAL,
            exit_reason TEXT,
            FOREIGN KEY (ticker) REFERENCES universe(ticker)
        )
    """)
    
    # Logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME,
            event_type TEXT,
            details TEXT
        )
    """)
    
    # Create indexes for better performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_date ON metrics(date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_ticker ON metrics(ticker)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_status ON metrics(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp)")
    
    conn.commit()
    conn.close()

def log_event(event_type: str, details: dict):
    """Log an event to the logs table."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO logs (timestamp, event_type, details) VALUES (?, ?, ?)",
        (datetime.now(), event_type, json.dumps(details))
    )
    conn.commit()
    conn.close()

def get_sp500_universe():
    """Get all active S&P 500 tickers from universe."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT ticker, name, sector FROM universe WHERE is_active = 1")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def save_universe(tickers_data):
    """Save or update universe data."""
    conn = get_connection()
    cursor = conn.cursor()
    for ticker, name, sector in tickers_data:
        cursor.execute("""
            INSERT OR REPLACE INTO universe (ticker, name, sector, is_active)
            VALUES (?, ?, ?, 1)
        """, (ticker, name, sector))
    conn.commit()
    conn.close()

def save_metrics(metrics_data):
    """Save daily metrics for tickers."""
    conn = get_connection()
    cursor = conn.cursor()
    for metric in metrics_data:
        cursor.execute("""
            INSERT OR REPLACE INTO metrics 
            (date, ticker, price, ytd_return, one_month_return, two_week_return,
             momentum_persistence, rs_score, rs_trend, vol_30d, atr_pct, vol_regime,
             earnings_date, days_to_earnings, entry_score, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metric['date'], metric['ticker'], metric['price'],
            metric['ytd_return'], metric['one_month_return'], metric['two_week_return'],
            metric['momentum_persistence'], metric['rs_score'], metric['rs_trend'],
            metric['vol_30d'], metric['atr_pct'], metric['vol_regime'],
            metric.get('earnings_date'), metric.get('days_to_earnings'),
            metric['entry_score'], metric['status']
        ))
    conn.commit()
    conn.close()

def get_latest_metrics():
    """Get the latest metrics for all tickers."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.*, u.name, u.sector
        FROM metrics m
        JOIN universe u ON m.ticker = u.ticker
        WHERE m.date = (SELECT MAX(date) FROM metrics)
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_ticker_metrics(ticker: str):
    """Get latest metrics for a specific ticker."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.*, u.name, u.sector
        FROM metrics m
        JOIN universe u ON m.ticker = u.ticker
        WHERE m.ticker = ? AND m.date = (SELECT MAX(date) FROM metrics WHERE ticker = ?)
    """, (ticker, ticker))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def create_position(ticker: str, entry_price: float, rs_trend: str, vol_regime: str):
    """Create a new position."""
    stop_price = entry_price * 0.95
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO positions (ticker, entry_date, entry_price, stop_price, current_price, 
                              pnl_pct, rs_trend, vol_regime, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (ticker, datetime.now().date(), entry_price, stop_price, entry_price, 0.0,
          rs_trend, vol_regime, 'open'))
    conn.commit()
    position_id = cursor.lastrowid
    log_event('position_open', {'ticker': ticker, 'position_id': position_id, 'entry_price': entry_price})
    conn.close()
    return position_id

def get_positions(status=None):
    """Get positions, optionally filtered by status."""
    conn = get_connection()
    cursor = conn.cursor()
    if status:
        cursor.execute("""
            SELECT p.*, u.name, u.sector
            FROM positions p
            JOIN universe u ON p.ticker = u.ticker
            WHERE p.status = ?
        """, (status,))
    else:
        cursor.execute("""
            SELECT p.*, u.name, u.sector
            FROM positions p
            JOIN universe u ON p.ticker = u.ticker
        """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_position_price(ticker: str, current_price: float):
    """Update current price and P&L for a position."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT entry_price, stop_price FROM positions WHERE ticker = ? AND status = 'open'", (ticker,))
    row = cursor.fetchone()
    if row:
        entry_price, stop_price = row['entry_price'], row['stop_price']
        pnl_pct = ((current_price - entry_price) / entry_price) * 100
        
        # Check if stop loss triggered
        new_status = 'open'
        exit_reason = None
        if current_price <= stop_price:
            new_status = 'exit_required'
            exit_reason = '5_percent_rule'
            log_event('position_exit_signal', {
                'ticker': ticker,
                'current_price': current_price,
                'stop_price': stop_price,
                'reason': '5_percent_rule'
            })
        
        cursor.execute("""
            UPDATE positions 
            SET current_price = ?, pnl_pct = ?, status = ?
            WHERE ticker = ? AND status = 'open'
        """, (current_price, pnl_pct, new_status, ticker))
        conn.commit()
    conn.close()

def close_position(position_id: int, exit_price: float, exit_reason: str):
    """Close a position."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE positions 
        SET status = 'closed', exit_date = ?, exit_price = ?, exit_reason = ?
        WHERE id = ?
    """, (datetime.now().date(), exit_price, exit_reason, position_id))
    conn.commit()
    log_event('position_exit', {'position_id': position_id, 'exit_price': exit_price, 'reason': exit_reason})
    conn.close()

def get_logs(limit=100):
    """Get recent log entries."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM logs ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
