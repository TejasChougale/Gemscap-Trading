# Gemscap Trading – Real-Time Quantitative Analytics Dashboard

A complete real-time analytical system built as part of the Quant Developer Assignment.
This project ingests live Binance tick data, performs quantitative analytics, stores sampled data, and presents interactive visualizations through a Streamlit dashboard.

## 🚀 1. Overview

The system demonstrates an end-to-end quantitative workflow:

-   **Live tick ingestion** using Binance WebSocket
-   **Sampling** into OHLCV (1s, 1m, 5m)
-   **Advanced analytics**:
    -   Hedge Ratio (OLS)
    -   Spread & Z-Score
    -   Rolling Correlation
    -   ADF Stationarity Test
-   **Real-time dashboard** for traders
-   **Alert engine** for threshold-based triggers
-   **CSV export** for ticks & analytics
-   **Modular and scalable backend architecture**

## 🏗️ 2. Architecture

```
Binance WebSocket
        ↓
Ingestion Engine (Async)
        ↓
Storage Layer (SQLite + CSV)
        ↓
Resampling Engine (Tick → OHLCV)
        ↓
Analytics Engine
(OLS, Spread, Z-Score, ADF, Correlation)
        ↓
Streamlit Frontend
        ↓
Real-Time Charts, Stats, Alerts
```

**Files:**
-   `/docs/archdraw.io` (Source)

## 📦 3. Project Structure

```
Gemscap-Trading/
│── app.py                 # Streamlit dashboard
│── backend.py             # WebSocket ingest + pipelines
│── analytics.py           # OLS, Z-Score, ADF, correlation
│── alerts.py              # Rule-based alert engine
│── storage.py             # SQLite + CSV data layer
│── resampling.py          # Tick → OHLCV converter
│── data/                  # Saved tick & OHLCV
│── docs/                  # Architecture diagrams
│── requirements.txt
│── README.md
```

## ⚙️ 4. Installation

1.  **Clone the repository**
    ```bash
    git clone https://github.com/TejasChougale/Gemscap-Trading.git
    cd Gemscap-Trading
    ```

2.  **Create Virtual Environment**
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # Linux/Mac
    source venv/bin/activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

## ▶️ 5. Running the Application

1.  **Start the Dashboard**
    ```bash
    streamlit run app.py
    ```

2.  **Using the UI**
    -   Enter symbols (e.g., `BTCUSDT,ETHUSDT`)
    -   Select timeframe (tick, 1s, 1m, 5m)
    -   View Price, Spread, Z-Score, Correlation, ADF
    -   Configure alerts (e.g., `Z > 2`, `Spread < -10`)
    -   Download CSV data

## 📊 6. Analytics Implemented

### 1. Hedge Ratio (OLS Regression)
Used to establish pair relationships.

$$
Y = \beta X + \epsilon
$$

### 2. Spread

$$
Spread = Y - \beta X
$$

### 3. Z-Score

$$
Z = \frac{Spread - \mu}{\sigma}
$$

Where:
-   $\mu$ = Rolling mean
-   $\sigma$ = Rolling standard deviation

### 4. Rolling Correlation
Pearson correlation over a sliding window.

### 5. ADF Test
**Null Hypothesis:** Spread has unit root (not stationary).
**Interpretation:** p-value < 0.05 → Mean-reverting.

## 🔔 7. Alerts Engine

Rules can be defined such as:
-   `Z-Score > 2`
-   `Spread < -5`
-   `Price > 90000`

Alerts appear in:
-   Real-time dashboard
-   Alert history log

## 📤 8. Data Export

Exportable from the dashboard:
-   Tick-level data (CSV)
-   OHLCV data (CSV)
-   Analytics CSVs

## 🧪 9. Optional Extensions Implemented

-   Kalman filter dynamic hedge ratio (planned/experimental)
-   Heatmaps for multi-symbol correlation
-   Mini mean-reversion backtest
-   Liquidity filters
-   Visual summaries for alerts

## 📝 10. Methodology

The design follows assignment guidelines:
-   Modular, scalable backend
-   WebSocket ingestion decoupled from analytics
-   Asynchronous I/O for real-time performance
-   Clear separation: ingest → store → resample → analyze → visualize
-   Extensible pipeline for additional analytics

## 🤖 11. ChatGPT Usage Transparency

ChatGPT was used for:
-   Debugging ingestion + async logic
-   Optimizing analytics functions
-   README structuring & documentation
-   Designing architecture outline
-   Boilerplate code cleanup

Prompts focused on:
-   Improving modularity
-   Ensuring assignment compliance
-   Visualizing architecture

## 📚 12. Requirements

-   `python >= 3.8`
-   `streamlit`
-   `pandas`
-   `numpy`
-   `plotly`
-   `statsmodels`
-   `aiosqlite`
-   `aiohttp`

## 📜 13. License

This project is released under the MIT License.
