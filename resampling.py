# resampling.py
import pandas as pd
import plotly.graph_objects as go
from typing import Tuple

def ticks_to_ohlcv(df: pd.DataFrame, timeframe_ms: int) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    if not pd.api.types.is_datetime64_any_dtype(df.index):
        df.index = pd.to_datetime(df.index, utc=True)
    freq = f"{int(timeframe_ms)}ms"
    agg = {"price": ["first","max","min","last"]}
    if "size" in df.columns:
        agg["size"] = "sum"
    res = df.resample(freq).apply(agg)
    if res.empty:
        return pd.DataFrame()
    res.columns = ["_".join(c).strip() for c in res.columns.values]
    ohlcv = pd.DataFrame({
        "open": res["price_first"],
        "high": res["price_max"],
        "low": res["price_min"],
        "close": res["price_last"],
        "volume": res["size_sum"] if "size_sum" in res.columns else 0.0
    }, index=res.index)
    ohlcv.dropna(subset=["open"], inplace=True)
    return ohlcv

def ohlcv_to_plotly(ohlcv):
    if ohlcv is None or ohlcv.empty:
        return None, None
    x = ohlcv.index
    fig = go.Figure(data=[go.Candlestick(x=x,
                                         open=ohlcv["open"],
                                         high=ohlcv["high"],
                                         low=ohlcv["low"],
                                         close=ohlcv["close"],
                                         increasing_line_color='#26a69a', decreasing_line_color='#ef5350')])
    fig.update_layout(margin=dict(l=10,r=10,t=20,b=20), height=420, template='plotly_dark')
    fig_vol = go.Figure()
    fig_vol.add_trace(go.Bar(x=x, y=ohlcv["volume"]))
    fig_vol.update_layout(margin=dict(l=10,r=10,t=10,b=20), height=120, template='plotly_dark')
    return fig, fig_vol
