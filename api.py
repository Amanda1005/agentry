"""
Agentry FastAPI backend
Run locally: uvicorn api:app --reload --port 8000
"""

import os
import re
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query, Request, Body
from pydantic import BaseModel
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import pandas as pd
import xgboost as xgb
from sqlalchemy import text

from src.db.models import get_engine
from src.features.fetch_transfers import _fetch_direction
from src.features.compute_features import compute
from src.models.train import FEATURE_COLS

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Agentry API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_model: xgb.XGBClassifier | None = None

def get_model() -> xgb.XGBClassifier:
    global _model
    if _model is None:
        _model = xgb.XGBClassifier()
        _model.load_model("models/xgb_base.json")
    return _model


CHAIN_MAP = {
    "base":     "base",
    "ethereum": "ethereum",
    "arbitrum": "arbitrum",
    "optimism": "optimism",
    "polygon":  "polygon",
}

ADDRESS_RE = re.compile(r'^0x[0-9a-fA-F]{40}$')


# ── Stats ──────────────────────────────────────────────────────────────────────

@app.get("/api/stats")
@limiter.limit("30/minute")
def get_stats(request: Request):
    engine = get_engine()
    with engine.connect() as conn:
        total = conn.execute(text(
            "SELECT COUNT(*) FROM wallet_features WHERE chain='base'"
        )).scalar()
        n_high = conn.execute(text(
            "SELECT COUNT(*) FROM wallet_features WHERE chain='base' AND agent_score >= 80"
        )).scalar()
        pct = conn.execute(text(
            "SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE agent_score >= 50) / COUNT(*), 1) "
            "FROM wallet_features WHERE chain='base'"
        )).scalar()
    return {
        "total_wallets":    total,
        "high_confidence":  n_high,
        "pct_agentic":      float(pct or 0),
        "roc_auc":          0.94,
    }


# ── Leaderboard ────────────────────────────────────────────────────────────────

@app.get("/api/leaderboard")
@limiter.limit("30/minute")
def get_leaderboard(request: Request, limit: int = Query(50, le=200)):
    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql(text("""
            SELECT lw.address, lw.label, wf.agent_score,
                   wf.transfer_total, wf.active_days, wf.active_hours,
                   wf.unique_counterparties, wf.inter_tx_cv
            FROM labeled_wallets lw
            JOIN wallet_features wf ON lw.address = wf.address AND lw.chain = wf.chain
            WHERE lw.chain = 'base' AND wf.agent_score >= 50
            ORDER BY wf.agent_score DESC
            LIMIT :lim
        """), conn, params={"lim": limit})
    return df.to_dict(orient="records")


# ── Distribution ───────────────────────────────────────────────────────────────

@app.get("/api/distribution")
@limiter.limit("30/minute")
def get_distribution(request: Request):
    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql(text("""
            SELECT lw.label, wf.agent_score
            FROM labeled_wallets lw
            JOIN wallet_features wf ON lw.address = wf.address AND lw.chain = wf.chain
            WHERE lw.chain = 'base' AND wf.agent_score IS NOT NULL
        """), conn)
    df["bin"] = (df["agent_score"] // 5 * 5).astype(int)
    hist = df.groupby(["bin", "label"]).size().reset_index(name="count")
    return hist.to_dict(orient="records")


# ── Score wallet ───────────────────────────────────────────────────────────────

@app.get("/api/score")
@limiter.limit("10/minute")
def score_wallet(
    request: Request,
    address: str = Query(..., min_length=42, max_length=42),
    chain:   str = Query("base"),
):
    if not ADDRESS_RE.match(address):
        raise HTTPException(400, "Invalid Ethereum address format.")

    if chain not in CHAIN_MAP:
        raise HTTPException(400, "Unsupported chain.")

    chain_key = CHAIN_MAP[chain]
    addr = address.lower()

    engine = get_engine()
    if chain_key == "base":
        with engine.connect() as conn:
            row = conn.execute(text("""
                SELECT wf.agent_score, wf.transfer_total, wf.active_days, wf.active_hours,
                       wf.night_ratio, wf.weekend_ratio, wf.unique_counterparties,
                       wf.unique_tokens, wf.top_token_ratio, wf.inter_tx_cv, lw.label
                FROM wallet_features wf
                LEFT JOIN labeled_wallets lw ON lw.address = wf.address AND lw.chain = wf.chain
                WHERE wf.address = :addr AND wf.chain = 'base'
            """), {"addr": addr}).fetchone()
    else:
        with engine.connect() as conn:
            row = conn.execute(text("""
                SELECT agent_score, transfer_total, active_days, active_hours,
                       night_ratio, weekend_ratio, unique_counterparties,
                       unique_tokens, top_token_ratio, inter_tx_cv, NULL AS label
                FROM cross_chain_scores
                WHERE address = :addr AND chain = :chain
            """), {"addr": addr, "chain": chain_key}).fetchone()

    if row:
        data = dict(row._mapping)
        data["validated"] = chain_key == "base"
        data["chain"] = chain_key
        return data

    # Live score via Alchemy
    txs = _fetch_direction(addr, "from", chain_key) + _fetch_direction(addr, "to", chain_key)
    if not txs:
        raise HTTPException(404, "No transfer activity found for this address.")

    rows = []
    for t in txs:
        ts = t.get("metadata", {}).get("blockTimestamp", "")
        rows.append({
            "wallet_address": addr,
            "block_time":     datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else None,
            "from_address":   (t.get("from") or "").lower(),
            "to_address":     (t.get("to") or "").lower(),
            "token_address":  (t.get("rawContract", {}).get("address") or "").lower(),
        })

    df_w = pd.DataFrame(rows)
    df_w["block_time"] = pd.to_datetime(df_w["block_time"], utc=True)
    feat = compute(df_w, addr)

    if feat is None:
        return {"agent_score": 0.0, "chain": chain_key, "validated": chain_key == "base",
                "label": "unknown"}

    X = pd.DataFrame([{c: feat.get(c) for c in FEATURE_COLS}]).astype(float)
    score = float(get_model().predict_proba(X)[:, 1][0]) * 100
    feat["agent_score"] = round(score, 1)
    feat["chain"] = chain_key
    feat["validated"] = chain_key == "base"
    feat["label"] = "unknown"
    return feat


# ── AI Wallet Analysis (Azure AI Foundry / Foundry IQ) ─────────────────────────

class ScorePayload(BaseModel):
    agent_score: float
    active_days: Optional[float] = None
    active_hours: Optional[float] = None
    transfer_total: Optional[float] = None
    night_ratio: Optional[float] = None
    weekend_ratio: Optional[float] = None
    unique_counterparties: Optional[float] = None
    unique_tokens: Optional[float] = None
    top_token_ratio: Optional[float] = None
    inter_tx_cv: Optional[float] = None


@app.post("/api/analyze")
@limiter.limit("5/minute")
def analyze_wallet_ai(
    request: Request,
    address: str = Query(..., min_length=42, max_length=42),
    chain:   str = Query("base"),
    body:    ScorePayload = Body(...),
):
    if not ADDRESS_RE.match(address):
        raise HTTPException(400, "Invalid Ethereum address format.")

    if chain not in CHAIN_MAP:
        raise HTTPException(400, "Unsupported chain.")

    from src.agents.wallet_analyst import analyze_wallet
    try:
        return analyze_wallet(address, CHAIN_MAP[chain], body.model_dump())
    except ValueError:
        raise HTTPException(503, "AI analysis unavailable: GITHUB_TOKEN not configured.")
    except Exception:
        raise HTTPException(500, "AI analysis temporarily unavailable.")
