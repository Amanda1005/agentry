# Cross-chain wallet sampling and scoring.
# For each non-Base EVM chain:
#   1. Sample active wallets by querying senders to Uniswap Universal Router
#   2. Score each wallet with the Base-trained behavioral model
#   3. Store results in cross_chain_scores
#
# Run: python -m src.features.fetch_cross_chain
#
# Note: model trained on Base — cross-chain scores are indicative (Beta).

import time
import requests
import pandas as pd
import xgboost as xgb
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.db.models import CrossChainScore, get_engine, create_tables
from src.features.fetch_transfers import _fetch_direction, ALCHEMY_ENDPOINTS
from src.features.compute_features import compute
from src.models.train import FEATURE_COLS

# Uniswap Universal Router — deployed at same address on all major EVM chains
UNISWAP_ROUTER = "0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD"

CHAINS   = [c for c in ALCHEMY_ENDPOINTS if c != "base"]
SAMPLE   = 500    # wallets per chain
WORKERS  = 8
DELAY    = 0.08


# ── Step 1: sample active wallets ────────────────────────────────────────────

def _sample_wallets(chain: str, target: int = SAMPLE) -> list[str]:
    """Get active wallet addresses by collecting senders to Uniswap Router."""
    url       = ALCHEMY_ENDPOINTS[chain]
    addresses = set()
    page_key  = None

    while len(addresses) < target * 4:   # oversample, filter later
        body = {
            "id": 1, "jsonrpc": "2.0",
            "method": "alchemy_getAssetTransfers",
            "params": [{
                "toAddress": UNISWAP_ROUTER,
                "category":  ["erc20"],
                "maxCount":  "0x3e8",
                "withMetadata": False,
                **({"pageKey": page_key} if page_key else {}),
            }],
        }
        try:
            resp   = requests.post(url, json=body, timeout=30)
            result = resp.json().get("result", {})
            for t in result.get("transfers", []):
                if t.get("from"):
                    addresses.add(t["from"].lower())
            page_key = result.get("pageKey")
            if not page_key:
                break
        except Exception:
            break
        time.sleep(DELAY)

    return list(addresses)[:target]


# ── Step 2: score one wallet ──────────────────────────────────────────────────

def _score_wallet(address: str, chain: str, model: xgb.XGBClassifier) -> dict | None:
    try:
        txs = _fetch_direction(address, "from", chain) + _fetch_direction(address, "to", chain)
        if not txs:
            return None
        rows = []
        for t in txs:
            ts = t.get("metadata", {}).get("blockTimestamp", "")
            rows.append({
                "wallet_address": address.lower(),
                "block_time":     datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else None,
                "from_address":   (t.get("from") or "").lower(),
                "to_address":     (t.get("to") or "").lower(),
                "token_address":  (t.get("rawContract", {}).get("address") or "").lower(),
            })
        df_w = pd.DataFrame(rows)
        df_w["block_time"] = pd.to_datetime(df_w["block_time"], utc=True)
        feat = compute(df_w, address)
        if feat is None:
            return None
        X     = pd.DataFrame([{c: feat.get(c) for c in FEATURE_COLS}]).astype(float)
        score = float(model.predict_proba(X)[:, 1][0]) * 100
        return {
            "address":             address.lower(),
            "chain":               chain,
            "agent_score":         round(score, 1),
            "transfer_total":      feat.get("transfer_total"),
            "active_days":         feat.get("active_days"),
            "active_hours":        feat.get("active_hours"),
            "night_ratio":         feat.get("night_ratio"),
            "weekend_ratio":       feat.get("weekend_ratio"),
            "unique_counterparties": feat.get("unique_counterparties"),
            "unique_tokens":       feat.get("unique_tokens"),
            "top_token_ratio":     feat.get("top_token_ratio"),
            "inter_tx_cv":         feat.get("inter_tx_cv"),
        }
    except Exception:
        return None


# ── Step 3: orchestrate per chain ─────────────────────────────────────────────

def process_chain(chain: str, model: xgb.XGBClassifier) -> None:
    engine = get_engine()

    with Session(engine) as s:
        done_count = s.execute(
            text("SELECT COUNT(*) FROM cross_chain_scores WHERE chain = :c"), {"c": chain}
        ).scalar()

    if done_count >= SAMPLE:
        print(f"[{chain}] Already have {done_count} rows — skipping.")
        return

    print(f"[{chain}] Sampling {SAMPLE} active wallets from Uniswap Router…")
    addresses = _sample_wallets(chain, SAMPLE)
    print(f"[{chain}] Got {len(addresses)} addresses. Scoring…")

    completed = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(_score_wallet, addr, chain, model): addr for addr in addresses}
        for fut in as_completed(futures):
            result = fut.result()
            if result:
                with Session(engine) as s:
                    s.execute(
                        pg_insert(CrossChainScore).values([result]).on_conflict_do_nothing()
                    )
                    s.commit()
            completed += 1
            if completed % 100 == 0:
                print(f"  [{chain}] {completed}/{len(addresses)}")

    with Session(engine) as s:
        saved = s.execute(
            text("SELECT COUNT(*) FROM cross_chain_scores WHERE chain = :c"), {"c": chain}
        ).scalar()
    print(f"[{chain}] Done — {saved} wallets scored.")


# ── Main ──────────────────────────────────────────────────────────────────────

def run():
    create_tables()
    model = xgb.XGBClassifier()
    model.load_model("models/xgb_base.json")

    for chain in CHAINS:
        process_chain(chain, model)

    # Summary
    engine = get_engine()
    with Session(engine) as s:
        rows = s.execute(text("""
            SELECT chain,
                   COUNT(*)                                              AS wallets,
                   ROUND(AVG(agent_score)::numeric, 1)                  AS avg_score,
                   SUM(CASE WHEN agent_score >= 70 THEN 1 ELSE 0 END)  AS agents
            FROM cross_chain_scores
            GROUP BY chain ORDER BY chain
        """)).fetchall()

    print("\n── cross_chain_scores summary ──")
    print(f"{'chain':<12} {'wallets':>8} {'avg_score':>10} {'agents(≥70)':>12}")
    for chain, wallets, avg, agents in rows:
        print(f"{chain:<12} {wallets:>8} {avg:>10} {agents:>12}")


if __name__ == "__main__":
    run()
