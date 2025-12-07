# Gemscap Trading Dashboard

A realtime realtime cryptocurrency trading dashboard built with Python and Streamlit. This application ingests live market data from Binance, calculates advanced pair trading metrics (Spread, Z-Score, ADF Test), and provides a robust alerting system.

![Dashboard Preview](https://via.placeholder.com/800x400?text=Gemscap+Dashboard+Preview)

## Features

-   **Realtime Data**: Live candlestick and volume charts powered by WebSocket feeds.
-   **Statistical Arbitrage Tools**:
    -   Realtime Pair Spread & Z-Score calculation.
    -   Rolling Correlation & Beta (Hedge Ratio).
    -   Augmented Dickey-Fuller (ADF) Stationarity Test.
-   **Alert Engine**:
    -   Configurable alerts for Price, Z-Score, Spread, and more.
    -   Live alert feed, ticker, and history log.
-   **Data Management**:
    -   Export tick data to CSV/NDJSON.
    -   Buffer management for long-running sessions.

## Project Structure

-   `app.py`: Main Streamlit application and UI logic.
-   `backend.py`: Async WebSocket ingestor (Binance).
-   `analytics.py`: Statistical calculations (OLS, Spread, Z-Score).
-   `alerts.py`: Rule evaluation engine.
-   `storage.py`: Async SQLite and CSV persistence.
-   `resampling.py`: Tick-to-OHLCV conversion utilities.

## Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/TejasChougale/Gemscap-Trading.git
    cd Gemscap-Trading
    ```

2.  **Create a virtual environment** (optional but recommended):
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # Mac/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

1.  **Run the application**:
    ```bash
    streamlit run app.py
    ```

2.  **Using the Dashboard**:
    -   **Start**: Enter symbols (e.g., `BTCUSDT,ETHUSDT`) and click "Start" in the sidebar.
    -   **Navigation**: Use the top tabs to switch between Graphs, Statistics, Alerts, and History.
    -   **Alerts**: Configure rules in the sidebar and make sure to click **"Apply Rules"** to activate them.

## Technical Details & Formulas

The dashboard implements standard statistical arbitrage models.

### 1. Hedge Ratio (Beta)
The hedge ratio ($\beta$) is calculated using Ordinary Least Squares (OLS) regression between the two asset prices.
Price_Y = beta times Price_X + epsilon 
-   **Code Reference**: `analytics.ols_hedge_ratio`

### 2. Spread
The spread is the residual of the linear relationship, representing the deviation from the expected price ratio.
Spread = Price_Y - (\beta \times Price_X)
-   **Code Reference**: `analytics.spread_and_zscore`

### 3. Z-Score
The Z-Score measures how many standard deviations the current spread is from its moving average. It is used to identify mean-reversion opportunities.
Z = (Spread - mu)/(sigma)
Where:
-   mu = Rolling Mean of Spread (default 50-period)
-   sigma = Rolling Standard Deviation of Spread (default 50-period)
-   **Code Reference**: `analytics.spread_and_zscore`

### 4. Rolling Correlation
Calculates the Pearson correlation coefficient between the returns of the two assets over a rolling window.
-   **Code Reference**: `analytics.rolling_correlation`

### 5. ADF Test (Stationarity)
Performed using `statsmodels.tsa.stattools.adfuller`.
-   **Null Hypothesis**: The spread has a unit root (is non-stationary).
-   **Interpretation**: A p-value < 0.05 suggests the spread is stationary (mean-reverting), making it suitable for pairs trading.

### 6. Alert Logic
Alerts are evaluated on every tick update.
-   **Condition**: `Value [Operator] Threshold` (e.g., `Z-Score > 2.0`).
-   **Enabled Rules**: Only rules marked as "Enabled" are processed.

## Requirements

-   Python 3.8+
-   `streamlit`
-   `pandas`
-   `numpy`
-   `plotly`
-   `statsmodels`
-   `aiosqlite`
-   `aiohttp`

## License

[MIT License](LICENSE)
