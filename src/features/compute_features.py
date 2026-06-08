# Compute behavioral features from cached ERC-20 transfer data.
# Loads raw_transfers from Postgres, computes per-wallet features with pandas.

from datetime import datetime, timezone, timedelta

import numpy as np
import pandas as pd
from scipy.stats import entropy as scipy_entropy


WINDOW_DAYS = 90


def _entropy(series: pd.Series, n_bins: int) -> float:
    counts = series.value_counts(normalize=True)
    dist = [counts.get(i, 0) for i in range(n_bins)]
    return float(scipy_entropy([p + 1e-10 for p in dist]))


def compute(df: pd.DataFrame, wallet: str) -> dict | None:
    """Compute features for one wallet from its raw transfer DataFrame.

    df must have columns: block_time, from_address, to_address, token_address.
    Returns None if wallet has no activity in the window.
    """
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=WINDOW_DAYS)
    df = df[df["block_time"] >= cutoff].copy()
    if df.empty:
        return None

    df = df.sort_values("block_time").reset_index(drop=True)
    w = wallet.lower()

    n = len(df)
    out_mask = df["from_address"] == w
    in_mask  = df["to_address"]   == w

    counterparties = pd.concat([
        df.loc[out_mask, "to_address"],
        df.loc[in_mask,  "from_address"],
    ]).unique()

    token_counts    = df["token_address"].value_counts()
    top_token_ratio = float(token_counts.iloc[0] / n) if n else 0.0

    intervals = df["block_time"].diff().dt.total_seconds().dropna()
    if len(intervals) >= 2:
        iv_mean = float(intervals.mean())
        iv_std  = float(intervals.std())
        inter_cv   = iv_std / iv_mean if iv_mean > 0 else 0.0
        burstiness = (iv_std - iv_mean) / (iv_std + iv_mean) if (iv_std + iv_mean) > 0 else 0.0
    else:
        inter_cv = burstiness = None

    return {
        "address":              w,
        "window_days":          WINDOW_DAYS,
        "transfer_total":       n,
        "transfer_out":         int(out_mask.sum()),
        "transfer_in":          int(in_mask.sum()),
        "active_days":          df["block_time"].dt.date.nunique(),
        "active_hours":         df["block_time"].dt.hour.nunique(),
        "hour_entropy":         _entropy(df["block_time"].dt.hour, 24),
        "weekend_ratio":        float(df["block_time"].dt.dayofweek.isin([5, 6]).mean()),
        "night_ratio":          float((df["block_time"].dt.hour < 6).mean()),
        "inter_tx_cv":          inter_cv,
        "burstiness":           burstiness,
        "unique_counterparties": len(counterparties),
        "unique_tokens":        int(df["token_address"].nunique()),
        "top_token_ratio":      top_token_ratio,
    }
