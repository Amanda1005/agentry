# Agentry

An agentic wallet observatory. Identifies and profiles wallets that exhibit
autonomous, agent-like behavior on Base, and scores any EVM wallet against
that baseline.

## Honest framing (keep this consistent everywhere)
This project does NOT claim to definitively identify "AI agents." On-chain we
cannot cleanly separate LLM-driven agents, trading bots, MEV bots, protocol
keepers, and CEX automation. What we CAN do is detect and score *agentic /
automated* behavior and validate it against known agent wallets. All README,
UI copy, and docs use "agentic / automated wallet intelligence" framing —
never overclaim.

## Chain scope

| Chain | Status | Ground truth source | Model |
|-------|--------|--------------------|----|
| Base | ✅ Complete | Virtuals ERC-6551 + ACP (~1,606 wallets) | `models/xgb_base.json` ROC-AUC 0.94 |
| Ethereum / Arbitrum / Optimism / Polygon | ⚡ Experimental | Base model applied cross-chain | Same model, unvalidated |

**Architecture:** One validated model (Base). Applied cross-chain for
experimental scoring. Each non-Base result is clearly labeled experimental.

**Why not other chains:**
- Ethereum: Olas agent EOAs have zero tx history (signing keys only).
  No other viable ground truth registry found.
- Solana: No public registry of known agent wallets found at usable scale.
  Two known addresses exist (Truth Terminal, Pump.fun Mayhem) — too few to train.
  Revisit when ecosystem matures.

## Tech stack
- Python (pandas, scikit-learn, xgboost), Postgres, Streamlit
- SHAP for model explainability
- Claude API for the LLM layer (wallet dossiers + plain-language score reasons)
- Data: Dune Analytics (primary), Alchemy RPC (wallet feature fetch)

## Data — Base

- **Positive labels:** Virtuals ERC-6551 TBAs + ACP-active wallets (~1,606 total)
- **Negative labels:** ~70 MEV bots + 1,000 random EOAs
- **Source:** Dune (cached in Postgres), Alchemy
- Cache all fetched data in Postgres. Do NOT re-query Dune (free-tier limits).

## Modeling

- Positive-Unlabeled (PU) learning framing: positives = known agents,
  unlabeled = everyone else. Never pretend unlabeled == negative.
- Output: calibrated agent-likelihood score 0–100.
- Always pair scores with SHAP feature importance.
- Validation: recall@k, negative controls score low, documented limitations.

## Key behavioral features
- Temporal: inter-tx interval regularity (inter_tx_cv), hour-of-day entropy,
  24/7 coverage, burstiness
- Volume: transfer_total, active_days, active_hours
- Diversity: unique_counterparties, unique_tokens, top_token_ratio
- ACP participation flag (Base only)

## Dashboard structure
- **Main page:** chain selector + wallet address input → score + behavioral fingerprint
  - Base: fully validated result
  - Other EVM chains: scored with Base model, labeled "Experimental"
- **Analytics page:** score distribution by label (Base only)
- **Leaderboard page:** top-scoring Base wallets

## Project structure

```
src/
  labels/         # Ground truth label fetching (Base only)
    fetch_virtuals.py     Virtuals ERC-6551 TBA addresses (Dune)
    fetch_acp.py          ACP-active wallet addresses (Dune)
    fetch_negatives.py    MEV bots, EOAs, CEX wallets (Dune + BaseScan)
    load_labels.py        Orchestrates all label fetching → Postgres
    sql/                  Dune SQL queries (01–07)
  features/       # Feature engineering
    fetch_transfers.py    ERC-20 transfer history via Alchemy (multi-chain)
    compute_features.py   Behavioral features from transfer data
    load_features.py      Orchestrates fetch + compute → wallet_features table
    fetch_cross_chain.py  Cross-chain wallet scoring (experimental)
  models/
    train.py              RF baseline + XGBoost + SHAP
  db/
    models.py             SQLAlchemy ORM (multi-chain schema)
  utils/
    dune_client.py        Dune API client
models/
  xgb_base.json           Trained Base model
app.py                    Streamlit dashboard
```

## Current phase
Dashboard polish + deployment.
1. Refactor app.py into multi-page Streamlit (pages/).
2. Main page: chain selector + wallet lookup.
3. Analytics + Leaderboard as sub-pages.
4. Update copy to reflect Base-core + EVM experimental framing.

## Conventions
- Keep all copy honest and non-exaggerated.
- Repo pushed to github.com/Amanda1005.
- Methodology transparency is a core differentiator vs Nansen/Arkham —
  document data sources, model, and limitations openly.

## Working style
Act as both a senior Web3 data scientist and a strict reviewer. Challenge
assumptions, flag unreliable data sources or methods, and verify facts by
searching the web rather than guessing. Do not agree just to please.
