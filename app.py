# app.py
import streamlit as st
import queue
import time
import json
import pandas as pd
import os
import math
import threading

from backend import BinanceIngestor
from resampling import ticks_to_ohlcv, ohlcv_to_plotly
from analytics import ols_hedge_ratio, spread_and_zscore, rolling_correlation
import alerts as alert_engine

# autorefresh helper (component may raise duplicate-key if recreated; handle defensively)
from streamlit_autorefresh import st_autorefresh
from streamlit.errors import StreamlitDuplicateElementKey

st.set_page_config(layout="wide", page_title="Realtime Candles — Dashboard", initial_sidebar_state="expanded")

# ---------- session defaults ----------
if 'ingestor' not in st.session_state:
    st.session_state.ingestor = None
if 'q' not in st.session_state:
    st.session_state.q = queue.Queue()
if 'buffer' not in st.session_state:
    st.session_state.buffer = []
if 'snapshot' not in st.session_state:
    st.session_state.snapshot = {}
if 'started_at' not in st.session_state:
    st.session_state.started_at = None
if 'display_paused' not in st.session_state:
    st.session_state.display_paused = False
if 'db_clear_requested' not in st.session_state:
    st.session_state.db_clear_requested = False
if 'alert_rules' not in st.session_state:
    st.session_state.alert_rules = []
if 'alert_events' not in st.session_state:
    st.session_state.alert_events = []

# internal flags
if '_shutting_down' not in st.session_state:
    st.session_state._shutting_down = False
if '_cleared' not in st.session_state:
    st.session_state._cleared = False

# ---------- autorefresh (defensive) ----------
AUTORUN_INTERVAL_MS = 800
try:
    # use a unique key for the autorefresh component to avoid duplication
    st_autorefresh(interval=AUTORUN_INTERVAL_MS, limit=None, key="autorefresh_main_v1")
except StreamlitDuplicateElementKey:
    # if key is already registered (rare), skip autorefresh to avoid crash
    st.sidebar.warning("autorefresh already present — skipping duplicate registration.")
except Exception:
    # any other component error should not crash the app
    st.sidebar.warning("autorefresh component could not be registered.")

# ---------- sidebar controls ----------
with st.sidebar:
    st.title("Controls")


    symbols = st.text_input("Symbols (comma separated)", value="BTCUSDT,ETHUSDT")
    timeframe_label = st.selectbox("Timeframe", ["1s", "1m", "5m"], index=1)
    tf_map = {"1s": 1000, "1m": 60000, "5m": 300000}
    timeframe_ms = tf_map[timeframe_label]

    col1, col2 = st.columns(2)
    with col1:
        start_btn = st.button("Start")
    with col2:
        stop_btn = st.button("Stop")

    demo_mode_chk = st.checkbox("Enable Demo Mode (local testing)", value=False)
    inject_demo_btn = st.button("Inject Demo Tick")

    pause_display = st.checkbox("Pause Chart (freeze)", value=st.session_state.display_paused)
    st.session_state.display_paused = pause_display

    clear_btn = st.button("Clear (reset)")
    st.markdown("---")
    if st.checkbox("Delete DB on Clear (ticks.db)", value=False):
        st.session_state.db_clear_requested = True
    else:
        st.session_state.db_clear_requested = False

    st.markdown("---")
    st.subheader("Alert rules")
    if st.button("Add rule"):
        new = {
            "id": alert_engine.gen_rule_id(),
            "name": f"Rule {len(st.session_state.alert_rules)+1}",
            "metric": "zscore",
            "symbol": "",
            "side": ">",
            "threshold": 2.0,
            "window": 50,
            "enabled": True
        }
        st.session_state.alert_rules.append(new)

    for i, r in enumerate(st.session_state.alert_rules):
        with st.expander(f"{r.get('name')} ({r.get('metric')})", expanded=False):
            r['name'] = st.text_input(f"Name {i}", value=r.get('name'), key=f"ar_name_{i}")
            r['metric'] = st.selectbox(f"Metric {i}", options=['zscore','spread','price','rolling_corr','adf'],
                                       index=['zscore','spread','price','rolling_corr','adf'].index(r.get('metric','zscore')),
                                       key=f"ar_metric_{i}")
            # Parse global symbols for options
            sym_options = [s.strip().upper() for s in symbols.split(",") if s.strip()]
            current_sym = r.get('symbol','').strip().upper()
            if current_sym not in sym_options and sym_options:
                current_sym = sym_options[0]
            elif not sym_options:
                current_sym = ""
            
            # Use selectbox for symbol
            idx_sym = sym_options.index(current_sym) if current_sym in sym_options else 0
            r['symbol'] = st.selectbox(f"Symbol {i}", options=sym_options, index=idx_sym, key=f"ar_sym_{i}")
            r['side'] = st.selectbox(f"Operator {i}", options=['>','<','>=','<=','=='],
                                     index=['>','<','>=','<=','=='].index(r.get('side','>')), key=f"ar_side_{i}")
            r['threshold'] = float(st.number_input(f"Threshold {i}", value=float(r.get('threshold',0.0)), key=f"ar_thr_{i}"))
            r['window'] = int(st.number_input(f"Window {i}", value=int(r.get('window',50)), key=f"ar_win_{i}"))
            r['enabled'] = st.checkbox("Enabled", value=r.get('enabled',True), key=f"ar_en_{i}")
            colx, coly = st.columns(2)
            if colx.button("Delete rule", key=f"ar_del_{i}"):
                st.session_state.alert_rules.pop(i)
                try:
                    st.rerun()
                except Exception:
                    pass

    if st.session_state.alert_rules:
        if st.button("Apply Rules"):
            st.success("Rules applied successfully!")
            st.rerun()

    st.markdown("---")

    # NDJSON download
    download_ndjson = st.button("Download ticks NDJSON")
    st.markdown("Use Demo Mode for local testing if websockets blocked.")

# ---------- queue drain ----------
def drain_queue(q, buffer, max_append=200):
    appended = 0
    while appended < max_append:
        try:
            item = q.get_nowait()
        except Exception:
            break
        buffer.append(item)
        appended += 1
    
    # Cap buffer size to prevent indefinite growth
    MAX_BUFFER_SIZE = 5000
    if len(buffer) > MAX_BUFFER_SIZE:
        buffer[:] = buffer[-MAX_BUFFER_SIZE:]
        
    return appended

# ---------- snapshot ----------
def take_snapshot():
    syms_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    for sym in syms_list:
        df = pd.DataFrame([t for t in st.session_state.buffer if t['symbol'].upper() == sym])
        if df.empty:
            st.session_state.snapshot[sym] = None
            continue
        df['ts'] = pd.to_datetime(df['ts'], utc=True, errors='coerce')
        df.dropna(subset=['ts'], inplace=True)
        if df.empty:
            st.session_state.snapshot[sym] = None
            continue
        df.set_index('ts', inplace=True)
        ohlcv = ticks_to_ohlcv(df, timeframe_ms)
        st.session_state.snapshot[sym] = ohlcv.copy() if not ohlcv.empty else None

# ---------- helper fetch ----------
def fetch_price_series(sym: str):
    df = pd.DataFrame([t for t in st.session_state.buffer if t['symbol'].upper() == sym.upper()])
    if df.empty:
        return pd.Series(dtype=float)
    df['ts'] = pd.to_datetime(df['ts'], utc=True, errors='coerce')
    df.dropna(subset=['ts'], inplace=True)
    if df.empty:
        return pd.Series(dtype=float)
    df.set_index('ts', inplace=True)
    return df['price'].astype(float)

# ---------- pair metrics ----------
def compute_pair_metrics(left: str, right: str, window: int = 50):
    sL = fetch_price_series(left)
    sR = fetch_price_series(right)
    if sL.empty or sR.empty:
        return pd.Series(dtype=float), pd.Series(dtype=float), None
    sL1 = sL.resample('1S').last().ffill()
    sR1 = sR.resample('1S').last().ffill()
    beta = ols_hedge_ratio(sL1, sR1)
    spread, zscore = spread_and_zscore(sL1, sR1, beta=beta, window=window)
    adf_res = None
    try:
        from statsmodels.tsa.stattools import adfuller
        s = spread.dropna()
        if len(s) >= 10:
            r = adfuller(s)
            adf_res = {"adf_stat": float(r[0]), "pvalue": float(r[1]), "usedlag": int(r[2]), "nobs": int(r[3]), "crit": r[4]}
    except Exception:
        adf_res = None
    return spread, zscore, adf_res

# ---------- metrics provider for alerts ----------
def metrics_provider(rule):
    metric = rule.get("metric")
    sym_field = (rule.get("symbol") or "").strip().upper()
    try:
        if metric == "price":
            sym = sym_field or (symbols.split(",")[0].strip().upper() if symbols else None)
            if not sym:
                return None
            s = fetch_price_series(sym)
            if s.empty: return None
            return float(s.iloc[-1])
        if metric in ("zscore","spread","adf"):
            if ":" in sym_field:
                left,right = [p.strip().upper() for p in sym_field.split(":",1)]
            else:
                syms = [s.strip().upper() for s in symbols.split(",") if s.strip()]
                if len(syms) < 2:
                    return None
                left,right = syms[0], syms[1]
            spread,zscore,adf_res = compute_pair_metrics(left,right,window=rule.get("window",50))
            if metric == "spread":
                return float(spread.iloc[-1]) if not spread.empty else None
            if metric == "zscore":
                v = float(zscore.iloc[-1]) if not zscore.empty else None
                return v if not (v is None or math.isnan(v)) else None
            if metric == "adf":
                return float(adf_res['adf_stat']) if adf_res else None
        if metric == "rolling_corr":
            if ":" in sym_field:
                left,right = [p.strip().upper() for p in sym_field.split(":",1)]
            else:
                syms = [s.strip().upper() for s in symbols.split(",") if s.strip()]
                if len(syms) < 2:
                    return None
                left,right = syms[0], syms[1]
            sL = fetch_price_series(left).resample('1S').last().ffill()
            sR = fetch_price_series(right).resample('1S').last().ffill()
            corr = rolling_correlation(sL,sR,window=rule.get("window",50))
            return float(corr.iloc[-1]) if not corr.empty else None
    except Exception:
        return None
    return None

# ---------- evaluate rules ----------
def evaluate_and_record():
    rules = st.session_state.alert_rules
    if not rules:
        return []
    events = alert_engine.evaluate_rules(rules, metrics_provider)
    if events:
        # push events into session history
        st.session_state.alert_events.extend(events)
        # Cap alert history
        MAX_ALERT_HISTORY = 500
        if len(st.session_state.alert_events) > MAX_ALERT_HISTORY:
            st.session_state.alert_events[:] = st.session_state.alert_events[-MAX_ALERT_HISTORY:]
    return events

# ---------- non-blocking start/stop/clear ----------


def stop_ingestor():
    if not st.session_state.ingestor:
        return
    
    st.session_state.ingestor.stop(wait_seconds=1.0)
    st.session_state.ingestor = None
    take_snapshot() # save last state
    st.rerun()

def clear_all():
    if st.session_state.ingestor:
        st.session_state.ingestor.stop(wait_seconds=0.5)
        st.session_state.ingestor = None
    
    st.session_state.buffer = []
    st.session_state.snapshot = {}
    st.session_state.display_paused = False
    st.session_state.started_at = None
    st.session_state.alert_events = [] # also clear alerts
    
    if st.session_state.db_clear_requested:
        try:
            os.remove("ticks.db")
        except Exception:
            pass
            
            pass
            
    st.rerun()

# ---------- start/stop wiring ----------
if start_btn:
    syms = [s.strip().lower() for s in symbols.split(",") if s.strip()]
    if not syms:
        st.warning("Enter at least one symbol")
    else:
        # Stop existing if running
        if st.session_state.ingestor:
             st.session_state.ingestor.stop(wait_seconds=0.5)
             st.session_state.ingestor = None
             
        st.session_state.q = queue.Queue()
        st.session_state.buffer = []
        st.session_state.snapshot = {}
        st.session_state.alert_events = []
        st.session_state.started_at = time.time()
        
        ing = BinanceIngestor(symbols=syms, out_queue=st.session_state.q, db_path="ticks.db")
        ing.enable_demo_mode(bool(demo_mode_chk))
        st.session_state.ingestor = ing
        ing.start()
        time.sleep(0.1) # brief wait for thread start
        st.rerun()

if stop_btn:
    stop_ingestor()

if clear_btn:
    clear_all()
if inject_demo_btn:
    if st.session_state.ingestor:
        threading.Thread(target=lambda: st.session_state.ingestor.inject_demo_tick_sync(), daemon=True).start()
        st.success("Injected demo tick (background)")
    else:
        st.warning("Start ingestor first")



drain_queue(st.session_state.q, st.session_state.buffer, max_append=200)



if st.session_state.display_paused and (not st.session_state.snapshot):
    take_snapshot()



events_fired = evaluate_and_record()

# ---------- Main layout ----------
# Header first (placeholder)
header_ph = st.empty()

# Horizontal Navigation below header
page = st.radio("Navigate", ["Graphs", "Statistics", "Alerts", "History"], index=0, horizontal=True, label_visibility="collapsed")
st.markdown("---")

# Update header with dynamic title
header_ph.title(f"Realtime Candles — {page}")

if page == "Graphs":
    st.subheader("Candles & Volume")
    syms_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not syms_list:
        st.info("Enter symbols and press Start.")
    else:
        tabs = st.tabs(syms_list)
        for i, tab in enumerate(tabs):
            sym = syms_list[i]
            with tab:
                if st.session_state.display_paused and st.session_state.snapshot.get(sym) is not None:
                    ohlcv = st.session_state.snapshot[sym]
                else:
                    df = pd.DataFrame([t for t in st.session_state.buffer if t['symbol'].upper() == sym])
                    if df.empty:
                        st.info("No ticks yet for " + sym)
                        continue
                    df['ts'] = pd.to_datetime(df['ts'], utc=True, errors='coerce')
                    df.dropna(subset=['ts'], inplace=True)
                    if df.empty:
                        st.info("No valid timestamps yet.")
                        continue
                    df.set_index('ts', inplace=True)
                    ohlcv = ticks_to_ohlcv(df, timeframe_ms)

                if ohlcv is None or ohlcv.empty:
                    st.info("Not enough data to render candles.")
                    continue

                MAX_CANDLES = 200
                ohlcv_plot = ohlcv.tail(MAX_CANDLES) if len(ohlcv) > MAX_CANDLES else ohlcv
                fig_candle, fig_vol = ohlcv_to_plotly(ohlcv_plot)
                if fig_candle:
                    st.plotly_chart(fig_candle, use_container_width=True)
                if fig_vol:
                    st.plotly_chart(fig_vol, use_container_width=True)

        # Pair analytics under charts if >=2 symbols
        if len(syms_list) >= 2:
            left_sym, right_sym = syms_list[0], syms_list[1]
            st.markdown("### Pair analytics (Spread & Z-score)")
            spread, zscore, adf_res = compute_pair_metrics(left_sym, right_sym, window=50)
            
            p_col1, p_col2 = st.columns(2)
            with p_col1:
                if not spread.empty:
                    st.markdown("Spread")
                    st.line_chart(spread.tail(400))
                else:
                    st.info("Not enough pair data for spread chart.")
            with p_col2:
                if not zscore.empty:
                    st.markdown("Z-score")
                    st.line_chart(zscore.tail(400))
                else:
                    st.info("Not enough pair data for zscore chart.")
        else:
            st.info("Add a second symbol to see pair analytics")

    # Scrolling ticker (full width under charts)
    st.markdown("---")
    st.markdown("### Alert Ticker")
    # Build ticker text from last 10 alert events
    ticker_items = []
    for evt in st.session_state.alert_events[-20:]:
        short = f"{evt.get('metric')} {evt.get('symbol') or ''} {evt.get('value'):.4f}"
        ticker_items.append(short)
    ticker_text = "  |  ".join(ticker_items) if ticker_items else "(no alerts)"
    
    # CSS Marquee
    st.markdown("""
    <style>
    @keyframes marquee {
        0%   { transform: translate(100%, 0); }
        100% { transform: translate(-100%, 0); }
    }
    .marquee-container {
        width: 100%;
        overflow: hidden;
        white-space: nowrap;
        background: #0b1220;
        border-radius: 6px;
        padding: 8px;
        color: #e6eef8;
        font-family: monospace;
    }
    .marquee-content {
        display: inline-block;
        padding-left: 100%;
        animation: marquee 15s linear infinite;
    }
    .marquee-content:hover {
        animation-play-state: paused;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="marquee-container">
        <div class="marquee-content">{ticker_text}</div>
    </div>
    """, unsafe_allow_html=True)

elif page == "Statistics":
    st.subheader("Live Statistics")
    
    # Row 1: System Stats
    st.markdown("#### System")
    sys_c1, sys_c2, sys_c3 = st.columns(3)
    sys_c1.metric("Buffered Ticks", f"{len(st.session_state.buffer)}")
    sys_c2.metric("Total Alerts", f"{len(st.session_state.alert_events)}")
    sys_c3.metric("DB Status", "Connected" if st.session_state.ingestor else "Idle")

    st.markdown("---")
    
    # Row 2: Last Tick Details
    st.markdown("#### Latest Market Data")
    if st.session_state.buffer:
        last = st.session_state.buffer[-1]
        t_price = float(last.get('price', 0))
        t_size = float(last.get('size', 0))
        t_sym = last.get('symbol', 'N/A')
        t_ts = last.get('ts', 'N/A')
        
        lt_c1, lt_c2, lt_c3, lt_c4 = st.columns(4)
        lt_c1.metric("Symbol", t_sym)
        lt_c2.metric("Price", f"{t_price:.2f}")
        lt_c3.metric("Size", f"{t_size:.4f}")
        lt_c4.metric("Timestamp", str(t_ts).split('T')[-1].replace('Z','') if 'T' in str(t_ts) else str(t_ts))
    else:
        st.info("No market data available. Start the ingestor.")

    st.markdown("---")

    # Row 3: Pair Analytics
    st.markdown("#### Pair Analytics (Beta / Hedge)")
    syms_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if len(syms_list) >= 2:
        left_sym, right_sym = syms_list[0], syms_list[1]
        spread, zscore, adf_res = compute_pair_metrics(left_sym, right_sym, window=50)
        last_spread = float(spread.iloc[-1]) if not spread.empty else None
        last_z = float(zscore.iloc[-1]) if not zscore.empty else None
        
        pa_c1, pa_c2 = st.columns(2)
        pa_c1.metric(f"Spread ({left_sym}-{right_sym})", f"{last_spread:.6f}" if last_spread is not None else "N/A")
        pa_c2.metric("Z-Score (50-period)", f"{last_z:.4f}" if last_z is not None and not math.isnan(last_z) else "N/A", 
                     delta="Overbought" if last_z and last_z > 2 else ("Oversold" if last_z and last_z < -2 else "Neutral"))
        
        if adf_res:
            st.markdown("**ADF Stationarity Test**")
            # Flatten/Format ADF result
            flat_adf = {
                "Test Statistic": adf_res["adf_stat"],
                "P-Value": adf_res["pvalue"],
                "Lags Used": adf_res["usedlag"],
                "Observations": adf_res["nobs"],
                "Critical (1%)": adf_res["crit"].get("1%", float("nan")),
                "Critical (5%)": adf_res["crit"].get("5%", float("nan")),
                "Critical (10%)": adf_res["crit"].get("10%", float("nan"))
            }
            st.dataframe(pd.DataFrame([flat_adf]).style.format({
                "Test Statistic": "{:.4f}",
                "P-Value": "{:.6f}",
                "Lags Used": "{:.0f}",
                "Observations": "{:.0f}",
                "Critical (1%)": "{:.4f}",
                "Critical (5%)": "{:.4f}",
                "Critical (10%)": "{:.4f}"
            }))
        else:
            st.info("ADF Test: Needs more data or statsmodels.")
    else:
        st.warning(f"Add a second symbol to view pair analytics. Current: {syms_list}")

elif page == "Alerts":
    st.subheader("Active Alerts")
    
    col_feed, col_cards = st.columns([1,1])
    
    with col_feed:
        st.subheader("Live Feed")
        live_feed_limit = 30
        feed_items = list(reversed(st.session_state.alert_events[-live_feed_limit:]))
        if not feed_items:
            st.info("No alerts yet.")
        else:
            for e in feed_items:
                ts = e.get('ts')
                metric = e.get('metric')
                sym = e.get('symbol') or ""
                val = e.get('value')
                msg = f"[{ts}] {e.get('rule_name')} — {metric} {sym} {val:.6f}"
                st.markdown(f"<div style='font-family:monospace; padding:6px; background:#071428; border-radius:6px; margin-bottom:4px;'>{msg}</div>", unsafe_allow_html=True)

    with col_cards:
        st.subheader("Recent Cards")
        cards = list(reversed(st.session_state.alert_events[-3:]))
        if not cards:
            st.info("No recent alerts.")
        for c in cards:
            st.markdown(f"""
            <div style="background:#3b0b0b;color:#fff;padding:10px;border-radius:8px;margin-bottom:8px;">
                <strong>🚨 {c.get('rule_name')}</strong><br/>
                <small>{c.get('ts')}</small><br/>
                <div>Metric: {c.get('metric')} {c.get('symbol') or ''}</div>
                <div>Value: {c.get('value'):.6f} {c.get('side')} {c.get('threshold'):.6f}</div>
            </div>
            """, unsafe_allow_html=True)

elif page == "History":
    st.subheader("Data History")
    
    # NDJSON history
    st.markdown("### NDJSON Stream (Recent)")
    NDJSON_LIMIT = 300
    ndjson_lines = [json.dumps(x) for x in st.session_state.buffer[-NDJSON_LIMIT:]]
    ndjson_preview = "\n".join(ndjson_lines) if ndjson_lines else "(empty)"
    st.text_area("Content", value=ndjson_preview, height=300, key="ndjson_preview")
    
    st.markdown("---")
    st.subheader("Downloads")
    d_col1, d_col2 = st.columns(2)
    with d_col1:
        ndjson = "\n".join(json.dumps(x) for x in st.session_state.buffer)
        st.download_button("Download ticks NDJSON", data=ndjson, file_name=f"ticks_{int(time.time())}.ndjson", mime="application/x-ndjson")
    with d_col2:
        if st.session_state.buffer:
            df_export = pd.DataFrame(st.session_state.buffer)
            csv_data = df_export.to_csv(index=False).encode('utf-8')
            st.download_button("Download ticks CSV", data=csv_data, file_name=f"ticks_{int(time.time())}.csv", mime="text/csv")

    st.markdown("---")
    st.subheader("Detailed Alert Log")
    hist = list(reversed(st.session_state.alert_events[-200:]))
    if not hist:
        st.info("No alert events yet.")
    else:
        for h in hist[:20]:
            st.write(f"[{h['ts']}] {h['rule_name']} -> {h['message']}")
    
    if st.button("Export alert events (NDJSON)"):
        nd = "\n".join(json.dumps(x) for x in st.session_state.alert_events)
        st.download_button("Download alerts.ndjson", data=nd, file_name=f"alerts_{int(time.time())}.ndjson", mime="application/x-ndjson")



# show clearing status




# ---------- status ----------
if st.session_state.ingestor and st.session_state.ingestor.is_running():
    st.sidebar.success("Ingestor running")
else:
    st.sidebar.info("Ingestor stopped")

# simple CSV download helper (place in your app where appropriate)
import glob
csv_dir = "csv_data"
if os.path.isdir(csv_dir):
    files = sorted(glob.glob(os.path.join(csv_dir, "*.csv")))
    if files:
        st.subheader("CSV files")
        for p in files[-10:]:
            name = os.path.basename(p)
            if st.button(f"Download {name}"):
                with open(p, "rb") as f:
                    data = f.read()
                st.download_button(f"Download {name}", data=data, file_name=name, mime="text/csv")
