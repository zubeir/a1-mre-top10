# A1-MRE Online Rotational Dashboard

A Streamlit-based web dashboard for the A1-MRE (Monthly Rotational Engine) trading strategy. Tracks S&P 500 leadership, applies mechanical entry rules, and provides risk management with 5% stop-loss monitoring.

## Features

- **Rotational Scan**: View S&P 500 stocks ranked by Entry Score with filtering by sector, RS, volatility, and status
- **Ticker Detail**: Deep dive into individual stocks with price charts, momentum metrics, and entry decision support
- **Positions & Risk**: Monitor open positions with automated 5% stop-loss alerts
- **Performance & Modeling**: View modelled projected gain bands for qualified stocks

## Tech Stack

- **Frontend**: Streamlit
- **Backend**: Python
- **Data Source**: yfinance
- **Database**: SQLite
- **Scheduling**: APScheduler

## Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Initialize the database and populate initial data:
```bash
python update_data.py
```

4. Run the Streamlit app:
```bash
streamlit run app.py
```

## Deployment

### Streamlit Cloud

1. Push this repository to GitHub
2. Connect your GitHub account to [Streamlit Cloud](https://share.streamlit.io)
3. Create a new app pointing to this repository
4. The app will be deployed automatically

### Local Development

For local development with automated updates:

```bash
# Terminal 1: Run the scheduler
python scheduler.py

# Terminal 2: Run the Streamlit app
streamlit run app.py
```

## Data Updates

The dashboard requires daily market data updates:

- **Manual**: Run `python update_data.py` after market close
- **Automated**: The scheduler can be configured to run updates automatically

## Metrics & Rules

### Entry Score Calculation
- RS (30%), Momentum Persistence (30%), Volatility (15%), Trend (15%), Earnings (10%)
- Qualified if: RS ≥ 80, Persistence ≥ 70, Vol Regime ∈ {low, medium}, Days to earnings > 10, Entry Score ≥ 75

### Risk Management
- 5% stop-loss on all positions
- Automated monitoring and exit signals
- Manual confirmation required for exits

## Disclaimer

This dashboard is for informational purposes only. The A1-MRE strategy and all projections are modelled outputs, not financial advice. Past performance does not guarantee future results.

## License

Proprietary - For personal use only.
