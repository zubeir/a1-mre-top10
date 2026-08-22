"""
Scheduler for automated daily updates.
Uses APScheduler to run daily metrics updates and position monitoring.
"""

import sys
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import time

sys.path.append('.')

from database import get_positions, update_position_price, log_event
from data_fetcher import get_latest_price

def monitor_positions():
    """Monitor open positions and update prices/risk status."""
    print(f"Running position monitoring: {datetime.now()}")
    
    open_positions = get_positions(status='open')
    
    for pos in open_positions:
        try:
            current_price = get_latest_price(pos['ticker'])
            if current_price:
                update_position_price(pos['ticker'], current_price)
                print(f"Updated {pos['ticker']}: ${current_price:.2f}")
            time.sleep(0.1)
        except Exception as e:
            print(f"Error monitoring {pos['ticker']}: {e}")
    
    log_event('position_monitoring', {
        'timestamp': datetime.now().isoformat(),
        'positions_monitored': len(open_positions)
    })

def start_scheduler():
    """Start the background scheduler for automated tasks."""
    scheduler = BackgroundScheduler()
    
    # Schedule daily metrics update at 6:00 PM EST (after market close)
    scheduler.add_job(
        'update_data.update_daily_metrics',
        CronTrigger(hour=18, minute=0),
        id='daily_metrics_update',
        name='Daily Metrics Update',
        replace_existing=True
    )
    
    # Schedule position monitoring every 30 minutes during trading hours
    scheduler.add_job(
        monitor_positions,
        CronTrigger(day_of_week='mon-fri', hour='9-16', minute='*/30'),
        id='position_monitoring',
        name='Position Monitoring',
        replace_existing=True
    )
    
    scheduler.start()
    print("Scheduler started. Jobs scheduled:")
    print("- Daily metrics update: 6:00 PM EST")
    print("- Position monitoring: Every 30 min (9 AM - 4 PM EST, Mon-Fri)")
    
    return scheduler

if __name__ == "__main__":
    # For testing, run position monitoring once
    monitor_positions()
