# Orchestration: fetch transfers → compute features → load into wallet_features.
# Supports multi-chain: pass chain='ethereum' for Ethereum labels.
#
# Run (Base):     python -m src.features.load_features
# Run (Ethereum): python -m src.features.load_features --chain ethereum

import argparse
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.db.models import WalletFeatures, get_engine, create_tables
from src.features.fetch_transfers import fetch_all_wallets
from src.features.compute_features import compute


def load_all(chain: str = "base") -> None:
    create_tables()
    engine = get_engine()

    # 1. Get labeled wallets for this chain
    # CEX hot wallets: cap at 200 — enough for negative controls,
    # avoids fetching massive Ethereum CEX transfer histories.
    CEX_LIMIT = 200
    with Session(engine) as s:
        non_cex = s.execute(text(
            "SELECT address, label FROM labeled_wallets "
            "WHERE chain = :chain AND label != 'cex_hot_wallet'"
        ), {"chain": chain}).fetchall()
        cex = s.execute(text(
            "SELECT address, label FROM labeled_wallets "
            "WHERE chain = :chain AND label = 'cex_hot_wallet' "
            "ORDER BY RANDOM() LIMIT :lim"
        ), {"chain": chain, "lim": CEX_LIMIT}).fetchall()
    rows = non_cex + cex
    addresses = [r[0] for r in rows]
    label_map = {r[0]: r[1] for r in rows}
    print(f"[{chain}] Total wallets: {len(addresses)}")

    # 2. Fetch ERC-20 transfers via Alchemy (skips already-cached)
    fetch_all_wallets(addresses, chain=chain)

    # 3. Load raw transfers for this chain from Postgres
    print(f"[{chain}] Loading raw transfers from DB...")
    df_all = pd.read_sql(
        text("SELECT wallet_address, block_time, from_address, to_address, token_address "
             "FROM raw_transfers WHERE chain = :chain"),
        engine,
        params={"chain": chain},
    )
    df_all["block_time"] = pd.to_datetime(df_all["block_time"], utc=True)
    print(f"  {len(df_all):,} total transfer records loaded")

    # 4. Compute features per wallet
    print(f"[{chain}] Computing features...")
    feature_rows = []
    for addr in addresses:
        df_w = df_all[df_all["wallet_address"] == addr.lower()]
        feat = compute(df_w, addr)
        if feat is None:
            feat = {"address": addr.lower(), "window_days": 90}
        feat["chain"] = chain
        feat["is_acp_participant"] = (chain == "base" and label_map.get(addr) == "agent_acp")
        feature_rows.append(feat)

    # 5. Upsert into wallet_features
    all_cols = [c.key for c in WalletFeatures.__table__.columns
                if c.key not in ("address", "chain", "computed_at")]
    normalised = []
    for row in feature_rows:
        r = {c: row.get(c) for c in all_cols}
        r["address"] = row["address"]
        r["chain"]   = chain
        normalised.append(r)

    with Session(engine) as s:
        stmt = pg_insert(WalletFeatures).values(normalised)
        stmt = stmt.on_conflict_do_update(
            index_elements=["address", "chain"],
            set_={c: stmt.excluded[c] for c in all_cols},
        )
        s.execute(stmt)
        s.commit()
    print(f"  {len(normalised)} rows upserted into wallet_features")

    # 6. Summary
    with Session(engine) as s:
        summary = s.execute(text("""
            SELECT lw.label,
                   COUNT(*) AS wallets,
                   ROUND(AVG(wf.transfer_total)) AS avg_transfers,
                   ROUND(AVG(wf.active_days))    AS avg_active_days,
                   ROUND(AVG(wf.unique_counterparties)) AS avg_counterparties
            FROM labeled_wallets lw
            LEFT JOIN wallet_features wf ON lw.address = wf.address AND lw.chain = wf.chain
            WHERE lw.chain = :chain
            GROUP BY lw.label ORDER BY lw.label
        """), {"chain": chain}).fetchall()

    print(f"\n── wallet_features summary [{chain}] ──")
    print(f"{'label':<25} {'wallets':>8} {'avg_tx':>8} {'avg_days':>10} {'avg_cpty':>10}")
    for label, wallets, avg_tx, avg_days, avg_cpty in summary:
        print(f"{label:<25} {wallets:>8} {avg_tx or 0:>8} {avg_days or 0:>10} {avg_cpty or 0:>10}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--chain", default="base", choices=["base", "ethereum", "solana"])
    args = parser.parse_args()
    load_all(chain=args.chain)
