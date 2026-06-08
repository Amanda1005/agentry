# Orchestrates fetching from all sources and loading into labeled_wallets table.
# Run: python -m src.labels.load_labels

from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.db.models import LabeledWallet, get_engine, create_tables
from src.labels.fetch_virtuals import fetch_virtuals_tbas
from src.labels.fetch_acp import fetch_acp_agents
from src.labels.fetch_negatives import fetch_cex_wallets, fetch_mev_bots, fetch_eoa_sample


def _normalize(addr) -> str:
    if isinstance(addr, bytes):
        return "0x" + addr.hex().lower()
    s = str(addr).strip()
    return s.lower() if s.startswith("0x") else "0x" + s.lower()


def _upsert(session: Session, rows: list[dict]) -> int:
    if not rows:
        return 0
    stmt = pg_insert(LabeledWallet).values(rows)
    stmt = stmt.on_conflict_do_nothing(index_elements=["address", "chain"])
    result = session.execute(stmt)
    session.commit()
    return result.rowcount


def load_all():
    create_tables()
    engine = get_engine()

    with Session(engine) as session:
        # ── Positive labels (Base) ────────────────────────────────────────────

        print("Fetching Virtuals TBAs (agent_virtuals)...")
        tbas = fetch_virtuals_tbas()
        n = _upsert(session, [
            {
                "address":      _normalize(r["tba_address"]),
                "chain":        "base",
                "label":        "agent_virtuals",
                "label_source": "virtuals_erc6551_registry",
            }
            for r in tbas
        ])
        print(f"  → {n} rows inserted  (fetched {len(tbas)})")

        print("Fetching ACP agents (agent_acp)...")
        acp = fetch_acp_agents()
        n = _upsert(session, [
            {
                "address":      _normalize(r["agent_wallet"]),
                "chain":        "base",
                "label":        "agent_acp",
                "label_source": "acp_memo_event_ge1000",
                "notes":        f"memo_count={r['memo_count']}",
            }
            for r in acp
        ])
        print(f"  → {n} rows inserted  (fetched {len(acp)})")

        # ── Negative labels (Base) ────────────────────────────────────────────

        print("Fetching Base CEX wallets (BaseScan)...")
        try:
            cex = fetch_cex_wallets()
            n = _upsert(session, [
                {
                    "address":      r["address"],
                    "chain":        "base",
                    "label":        "cex_hot_wallet",
                    "label_source": "basescan_label",
                    "notes":        r.get("name", ""),
                }
                for r in cex
            ])
            print(f"  → {n} rows inserted  (fetched {len(cex)})")
        except Exception as e:
            print(f"  ⚠ CEX fetch failed: {e} — skipping (fix BASESCAN_API_KEY)")

        print("Fetching MEV bots (negative_mev)...")
        mev = fetch_mev_bots()
        n = _upsert(session, [
            {
                "address":      _normalize(r["address"]),
                "chain":        "base",
                "label":        "mev_bot",
                "label_source": "behavioral_high_block_density_7d",
                "notes":        f"tx_count={r['tx_count']},avg_per_block={r['avg_txs_per_block']}",
            }
            for r in mev
        ])
        print(f"  → {n} rows inserted  (fetched {len(mev)})")

        print("Fetching random EOA sample (eoa_sampled)...")
        eoa = fetch_eoa_sample()
        n = _upsert(session, [
            {
                "address":      _normalize(r["address"]),
                "chain":        "base",
                "label":        "eoa_sampled",
                "label_source": "random_active_eoa_90d",
                "notes":        f"tx_count={r['tx_count']}",
            }
            for r in eoa
        ])
        print(f"  → {n} rows inserted  (fetched {len(eoa)})")

        # ── Summary ───────────────────────────────────────────────────────────
        rows = session.execute(
            text("SELECT chain, label, COUNT(*) FROM labeled_wallets "
                 "GROUP BY chain, label ORDER BY chain, label")
        ).fetchall()
        print("\n── labeled_wallets summary ──")
        for chain, label, cnt in rows:
            print(f"  {chain:<12} {label:<25} {cnt:>6}")


if __name__ == "__main__":
    load_all()
