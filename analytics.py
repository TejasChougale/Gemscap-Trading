# analytics.py
import numpy as np
import pandas as pd
from typing import Tuple

def ols_hedge_ratio(y: pd.Series, x: pd.Series) -> float:
    df = pd.concat([y, x], axis=1).dropna()
    if df.empty:
        return 1.0
    Y = df.iloc[:,0].values
    X = df.iloc[:,1].values
    if np.all(X == 0):
        return 0.0
    A = np.vstack([X, np.ones(len(X))]).T
    beta, intercept = np.linalg.lstsq(A, Y, rcond=None)[0]
    return float(beta)

def spread_and_zscore(y: pd.Series, x: pd.Series, beta: float = None, window: int = 50) -> Tuple[pd.Series, pd.Series]:
    df = pd.concat([y, x], axis=1).dropna()
    if df.empty:
        return pd.Series(dtype=float), pd.Series(dtype=float)
    y_aligned = df.iloc[:,0]
    x_aligned = df.iloc[:,1]
    if beta is None:
        beta = ols_hedge_ratio(y_aligned, x_aligned)
    spread = y_aligned - beta * x_aligned
    rm = spread.rolling(window=window, min_periods=5).mean()
    rs = spread.rolling(window=window, min_periods=5).std()
    z = (spread - rm) / rs
    return spread, z

def rolling_correlation(s1: pd.Series, s2: pd.Series, window: int = 50) -> pd.Series:
    df = pd.concat([s1, s2], axis=1).dropna()
    if df.empty:
        return pd.Series(dtype=float)
    return df.iloc[:,0].rolling(window, min_periods=5).corr(df.iloc[:,1])
