"""
Agentry incremental sync — run weekly via Railway Cron.

What it does:
  1. Re-query Dune for latest Virtuals TBAs + ACP agents
  2. Detect newly appeared addresses (not yet in DB)
  3. Fetch ERC-20 transfer features for new addresses via Alchemy
  4. Score with existing xgb_base.json model
  5. Insert new rows into labeled_wallets + wallet_features

Does NOT retrain the model — scoring uses the existing xgb_base.json.
Model retraining is a manual step done when enough new labels accumulate.

Run locally : python sync.py
Railway Cron: 0 2 * * 1  (every Monday 02:00 UTC)
"""

import logging
import pandas as pd
import xgboost as xgb
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.db.models import get_engine, create_tables, LabeledWallet, WalletFeatures
from src.labels.fetch_virtuals import fetch_virtuals_tbas
from src.labels.fetch_acp import fetch_acp_agents
from src.features.fetch_transfers import _fetch_direction
from src.features.compute_features import compute
from src.models.train import FEATURE_COLS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

MODEL_PATH = "models/xgb_base.json"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _normalize(addr) -> str:
    if isinstance(addr, bytes):
        return "0x" + addr.hex().lower()
    s = str(addr).strip()
    return s.lower() if s.startswith("0x") else "0x" + s.lower()


def _load_model() -> xgb.XGBClassifier:
    m = xgb.XGBClassifier()
    m.load_model(MODEL_PATH)
    return m


def _score_address(addr: str, model: xgb.XGBClassifier) -> dict | None:
    """Fetch transfers, compute features, return scored feature dict or None."""
    txs = _fetch_direction(addr, "from", "base") + _fetch_direction(addr, "to", "base")
    if not txs:
        return None
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
        return None
    X     = pd.DataFrame([{c: feat.get(c) for c in FEATURE_COLS}]).astype(float)
    score = float(model.predict_proba(X)[:, 1][0]) * 100
    feat["agent_score"] = round(score, 1)
    feat["chain"]       = "base"
    return feat


# ── Sync steps ─────────────────────────────────────────────────────────────────

def sync_labels(engine) -> tuple[list[str], list[str]]:
    """
    Pull latest Virtuals + ACP addresses from Dune.
    Returns (new_virtuals, new_acp) — addresses not yet in labeled_wallets.
    """
    with engine.connect() as conn:
        existing = {
            r[0] for r in conn.execute(
                text("SELECT address FROM labeled_wallets WHERE chain = 'base'")
            ).fetchall()
        }

    log.info("Fetching Virtuals TBAs from Dune…")
    tbas = fetch_virtuals_tbas()
    virtuals_addrs = [_normalize(r["tba_address"]) for r in tbas]
    new_virtuals   = [a for a in virtuals_addrs if a not in existing]

    log.info("Fetching ACP agents from Dune…")
    acp_raw  = fetch_acp_agents()
    acp_addrs = [_normalize(r["agent_wallet"]) for r in acp_raw]
    acp_map   = {_normalize(r["agent_wallet"]): r["memo_count"] for r in acp_raw}
    new_acp   = [a for a in acp_addrs if a not in existing]

    log.info(f"New Virtuals: {len(new_virtuals)} | New ACP: {len(new_acp)}")

    # Insert new labels
    with Session(engine) as s:
        rows = [
            {"address": a, "chain": "base", "label": "agent_virtuals",
             "label_source": "virtuals_erc6551_registry"}
            for a in new_virtuals
        ] + [
            {"address": a, "chain": "base", "label": "agent_acp",
             "label_source": "acp_memo_event_ge1000",
             "notes": f"memo_count={acp_map.get(a, '?')}"}
            for a in new_acp
        ]
        if rows:
            s.execute(
                pg_insert(LabeledWallet).values(rows).on_conflict_do_nothing(
                    index_elements=["address", "chain"]
                )
            )
            s.commit()

    return new_virtuals, new_acp


def sync_features(engine, new_addresses: list[str]) -> int:
    """Fetch features + score for each new address. Returns number processed."""
    if not new_addresses:
        return 0

    model = _load_model()
    scored = 0

    all_cols = [c.key for c in WalletFeatures.__table__.columns
                if c.key not in ("address", "chain", "computed_at")]

    for addr in new_addresses:
        log.info(f"  Scoring {addr}…")
        feat = _score_address(addr, model)
        if feat is None:
            log.warning(f"  No transfer data for {addr} — skipping")
            continue

        row = {c: feat.get(c) for c in all_cols}
        row["address"] = addr
        row["chain"]   = "base"

        with Session(engine) as s:
            s.execute(
                pg_insert(WalletFeatures).values([row]).on_conflict_do_update(
                    index_elements=["address", "chain"],
                    set_={c: pg_insert(WalletFeatures).excluded[c] for c in all_cols},
                )
            )
            s.commit()
        scored += 1

    return scored


# ── Main ───────────────────────────────────────────────────────────────────────

def run():
    log.info("=== Agentry sync started ===")
    create_tables()
    engine = get_engine()

    new_virtuals, new_acp = sync_labels(engine)
    all_new = list(set(new_virtuals + new_acp))

    if not all_new:
        log.info("No new addresses found. DB is up to date.")
    else:
        log.info(f"Processing {len(all_new)} new addresses…")
        scored = sync_features(engine, all_new)
        log.info(f"Scored {scored}/{len(all_new)} new addresses.")

    # Summary
    with engine.connect() as conn:
        counts = conn.execute(text("""
            SELECT label, COUNT(*) FROM labeled_wallets
            WHERE chain = 'base' GROUP BY label ORDER BY label
        """)).fetchall()

    log.info("=== Current DB state ===")
    for label, cnt in counts:
        log.info(f"  {label:<25} {cnt:>6}")
    log.info("=== Sync complete ===")


if __name__ == "__main__":
    run()
