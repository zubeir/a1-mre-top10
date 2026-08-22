
# A1‑MRE Online Rotational Dashboard  
**Functional & Technical Specification**

---

## 1. Objective

Build and deploy an **online, always‑on web dashboard** for the **A1‑MRE (Monthly Rotational Engine)** strategy that:

- Tracks **S&P 500 leadership** (momentum, relative strength, volatility).
- Applies **mechanical entry rules** (no mid‑month chasing).
- Integrates **risk management**, including a **5% stop‑loss rule**.
- Provides **non‑advisory, modelled projected gain bands** for ranking.
- Is accessible via a **URL**, with no local installation required.

Primary user: **single institutional‑grade investor (Zubeir)**.

---

## 2. System architecture

### 2.1 Frontend

- **Framework:** Streamlit (preferred) or equivalent Python web UI.
- **Features:**
  - Interactive tables (sortable, filterable).
  - Multi‑page navigation.
  - Charts (price, equity curve, sector exposure).
  - Buttons for position actions (open/exit).

### 2.2 Backend

- **Language:** Python.
- **Responsibilities:**
  - Fetch market data (S&P 500 tickers, prices, earnings).
  - Compute metrics (returns, RS, volatility, Entry Score).
  - Apply A1‑MRE rules (qualification, risk flags).
  - Persist positions and logs.

### 2.3 Data

- **Universe:** S&P 500 constituents.
- **Source:** `yfinance` or equivalent market data API.
- **Data types:**
  - Daily prices.
  - Historical prices (for returns and volatility).
  - Earnings dates (if available via API).

### 2.4 Storage

- **Database:** SQLite or Postgres.
- **Core tables:**
  - `universe` – tickers, names, sectors.
  - `metrics` – daily metrics per ticker.
  - `positions` – open/closed trades.
  - `logs` – events (scans, signals, exits).

### 2.5 Deployment

- **Target:** Streamlit Cloud or similar PaaS.
- **Requirement:** Public or authenticated **URL** accessible via browser.

---

## 3. Data model

### 3.1 Table: `universe`

- `ticker` (string, PK)
- `name` (string)
- `sector` (string)
- `is_active` (bool)

### 3.2 Table: `metrics` (daily per ticker)

- `id` (PK)
- `date` (date)
- `ticker` (FK → `universe.ticker`)
- `price` (float)
- `ytd_return` (float, %)
- `one_month_return` (float, %)
- `two_week_return` (float, %)
- `momentum_persistence` (float, 0–100)
- `rs_score` (float, 0–100)
- `rs_trend` (enum: `rising`, `flat`, `falling`)
- `vol_30d` (float, %)
- `atr_pct` (float, %)
- `vol_regime` (enum: `low`, `medium`, `high`)
- `earnings_date` (date, nullable)
- `days_to_earnings` (int, nullable)
- `entry_score` (float, 0–100)
- `status` (enum: `qualified`, `watch`, `excluded`)

### 3.3 Table: `positions`

- `id` (PK)
- `ticker` (FK → `universe.ticker`)
- `entry_date` (date)
- `entry_price` (float)
- `stop_price` (float)  // 5% rule
- `current_price` (float)
- `pnl_pct` (float, %)
- `rs_trend` (enum)
- `vol_regime` (enum)
- `status` (enum: `open`, `exit_required`, `closed`)
- `exit_date` (date, nullable)
- `exit_price` (float, nullable)
- `exit_reason` (string, e.g. `5_percent_rule`)

### 3.4 Table: `logs`

- `id` (PK)
- `timestamp` (datetime)
- `event_type` (string, e.g. `scan_run`, `position_open`, `position_exit_signal`, `position_exit`)
- `details` (JSON/text)

---

## 4. Metric definitions

### 4.1 Returns

- **YTD:**

  \[
  \text{YTD} = \frac{\text{price}_{\text{today}} - \text{price}_{\text{start of year}}}{\text{price}_{\text{start of year}}} \times 100
  \]

- **1‑Month:**

  \[
  \text{1M} = \frac{\text{price}_{\text{today}} - \text{price}_{\text{30 days ago}}}{\text{price}_{\text{30 days ago}}} \times 100
  \]

- **2‑Week:**

  \[
  \text{2W} = \frac{\text{price}_{\text{today}} - \text{price}_{\text{10 trading days ago}}}{\text{price}_{\text{10 trading days ago}}} \times 100
  \]

### 4.2 Momentum persistence (0–100)

- Compute percentile ranks (0–100) for YTD, 1M, 2W returns vs S&P 500 universe.
- Define:

  \[
  \text{Persistence} = \frac{\text{rank\_ytd} + \text{rank\_1m} + \text{rank\_2w}}{3}
  \]

### 4.3 Relative strength (RS)

- RS is percentile rank of each ticker’s **6‑month return** vs S&P 500 peers:

  \[
  \text{RS} = \text{percentile}(\text{6M return vs universe})
  \]

- **RS trend:**
  - Compare RS over last N snapshots (e.g. 10 days).
  - If RS increasing → `rising`, flat → `flat`, decreasing → `falling`.

### 4.4 Volatility

- **30‑day volatility:**
  - Standard deviation of daily returns over last 30 trading days (expressed as %).

- **ATR %:**
  - Average True Range over last 14 days ÷ current price × 100.

- **Volatility regime:**
  - `low` if vol_30d < universe median.
  - `medium` if between median and 75th percentile.
  - `high` if > 75th percentile.

### 4.5 Earnings proximity

- `days_to_earnings = (earnings_date - today)` in days (nullable if unknown).

### 4.6 Entry Score (0–100)

Composite score:

\[
\text{Entry Score} = w_1 \cdot \text{RS} + w_2 \cdot \text{Persistence} + w_3 \cdot \text{VolatilityFactor} + w_4 \cdot \text{TrendFactor} + w_5 \cdot \text{EarningsFactor}
\]

- Suggested weights:
  - \( w_1 = 0.3 \) (RS)
  - \( w_2 = 0.3 \) (Persistence)
  - \( w_3 = 0.15 \) (Volatility)
  - \( w_4 = 0.15 \) (Trend)
  - \( w_5 = 0.10 \) (Earnings)

- VolatilityFactor:
  - Low vol → 100  
  - Medium → 80  
  - High → 50  

- TrendFactor:
  - RS trend rising → 100  
  - Flat → 70  
  - Falling → 40  

- EarningsFactor:
  - Days_to_earnings > 10 → 100  
  - ≤ 10 → 40  

**Status classification:**

- `qualified` if:
  - RS ≥ 80  
  - Persistence ≥ 70  
  - Vol_regime ∈ {low, medium}  
  - Days_to_earnings > 10  
  - Entry Score ≥ 75  

- `watch` if RS ≥ 60 but fails one other condition.
- `excluded` otherwise.

---

## 5. Risk management logic

### 5.1 5% stop‑loss rule

On position open:

\[
\text{stop\_price} = \text{entry\_price} \times 0.95
\]

Monitoring:

- If `current_price ≤ stop_price`:
  - Set `status = exit_required` in `positions`.
  - Log event in `logs` with `event_type = "position_exit_signal"` and `exit_reason = "5_percent_rule"`.

### 5.2 Position status transitions

- `open` → `exit_required` when stop triggered.
- `exit_required` → `closed` when user confirms exit via UI.
- `open` → `closed` when user exits for other reasons (e.g. month‑end rebalance).

---

## 6. UI pages & behavior

### 6.1 Page: Rotational Scan

**Purpose:**  
Show current S&P 500 leadership and A1‑MRE qualification.

**Components:**

- **Filters:**
  - Sector (dropdown).
  - RS minimum (slider).
  - Volatility regime (multi‑select).
  - Status filter: `qualified / watch / excluded`.

- **Table: Leaders**

Columns:

- Ticker  
- Name  
- Sector  
- Price  
- YTD %  
- 1M %  
- 2W %  
- RS  
- Momentum Persistence  
- Volatility (30‑day %)  
- ATR %  
- Entry Score  
- Status  

**Interactions:**

- Sort by any column (default: Entry Score descending).
- Click row → navigate to **Ticker Detail**.

---

### 6.2 Page: Ticker Detail

**Purpose:**  
Deep dive on a single stock.

**Inputs:** `ticker`.

**Components:**

- Header: ticker, name, sector, current price.
- **Chart:** price history (1M/3M/6M/1Y) with 20/50/200‑day moving averages.
- **Panels:**
  - **Momentum:** YTD, 1M, 2W, persistence.
  - **RS:** RS score, RS trend.
  - **Volatility:** vol_30d, ATR %, vol_regime.
  - **Risk:** if position exists → entry price, stop price, current price, P&L %; earnings date, days_to_earnings.
  - **Entry decision box:**
    - Entry Score.
    - Status (`qualified / watch / excluded`).
    - Tags:
      - ✅ Strong RS (RS ≥ 80)  
      - ✅ Persistent momentum (Persistence ≥ 70)  
      - ⚠ High volatility (vol_regime = high)  
      - ⚠ Earnings soon (days_to_earnings ≤ 10)  
      - ❌ Entry score below threshold (Entry Score < 75)  

**Actions:**

- Button: “Open Position” → create row in `positions`.
- Button: “Mark Exit” → close position (set `status = closed`, record exit).

---

### 6.3 Page: Positions & Risk

**Purpose:**  
Monitor open positions and risk signals.

**Components:**

- **Table: Open positions**

Columns:

- Ticker  
- Entry date  
- Entry price  
- Current price  
- Stop price  
- P&L %  
- RS trend  
- Vol_regime  
- Status (`open / exit_required`)  

**Logic:**

- Highlight row red if `status = exit_required`.
- Highlight yellow if RS trend = `falling` or vol_regime = `high`.

**Actions:**

- Button per row: “Confirm Exit” → set `status = closed`, record `exit_date`, `exit_price`, log event.

---

### 6.4 Page: Performance & Modeling

**Purpose:**  
Show A1‑MRE performance vs S&P and modelled projected gain bands.

**Components:**

- **Equity curve chart:**
  - A1‑MRE portfolio vs S&P 500 index.

- **Summary stats:**
  - Total return.
  - Max drawdown.
  - Win rate.

- **Projected gain modeling table (for `qualified` names):**

Columns:

- Ticker  
- RS  
- Persistence  
- Vol_regime  
- TrendFactor  
- VolatilityFactor  
- Projected Gain Band  
- Confidence (Low/Medium/High)  

**Model (non‑predictive):**

\[
\text{Projected Gain (center)} = \text{Persistence\_norm} \times \text{VolatilityFactor} \times \text{TrendFactor}
\]

- Persistence_norm = Persistence / 100.
- VolatilityFactor:
  - Low → 1.0  
  - Medium → 0.8  
  - High → 0.6  
- TrendFactor:
  - Rising → 1.0  
  - Flat → 0.8  
  - Falling → 0.6  

Band: ±2–3% around center, clearly labelled as **model only, not a forecast**.

---

## 7. Scheduled jobs

### 7.1 Daily metrics update

- Run once per trading day (after close).
- Steps:
  1. Fetch latest prices for all tickers.
  2. Update returns (YTD, 1M, 2W).
  3. Recompute momentum persistence.
  4. Recompute RS and RS trend.
  5. Recompute volatility metrics and regimes.
  6. Update earnings dates and days_to_earnings.
  7. Recompute Entry Score and status.
  8. Store snapshot in `metrics`.
  9. Log `scan_run` event.

### 7.2 Position monitoring

- Run daily or intraday.
- Steps:
  1. For each `positions` row with `status = open`:
     - Fetch current price.
     - Update `current_price`, `pnl_pct`.
     - If `current_price ≤ stop_price`:
       - Set `status = exit_required`.
       - Log `position_exit_signal` with reason `5_percent_rule`.

---

## 8. Non-functional requirements

- **Accessibility:**  
  - Web URL, no local install required.

- **Security:**  
  - Optional login if needed; single‑user focus.

- **Performance:**  
  - Handle full S&P 500 universe with daily updates.

- **Transparency:**  
  - Clearly label projected gains as **modelled, non‑advisory**.

---
