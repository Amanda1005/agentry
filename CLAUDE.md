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
- **Backend:** FastAPI + SQLAlchemy + Postgres
- **ML:** XGBoost, scikit-learn, SHAP
- **Frontend:** Next.js (`frontend/`)
- **Deploy:** Railway (API + weekly sync cron via `sync.py`)
- **Analytics dashboard:** Streamlit removed; analytics now served via Next.js `/analytics` page
- **Data:** Dune Analytics (primary, cached in Postgres), Alchemy RPC (live wallet features)

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

## Frontend structure (Next.js)
- **`/` (index):** chain selector + wallet address input → score + behavioral fingerprint
  - Base: fully validated result
  - Other EVM chains: scored with Base model, labeled "Experimental"
- **`/analytics`:** score distribution by label (Base only)
- **`/leaderboard`:** top-scoring Base wallets
- **`/api/score`:** FastAPI endpoint backing all scoring requests

## Project structure

```
api.py                    FastAPI backend (scoring endpoint)
sync.py                   Weekly incremental data sync (Railway cron)
models/xgb_base.json      Trained XGBoost model
frontend/                 Next.js frontend
  pages/
    index.js              Wallet scorer (home)
    analytics.js          Score distribution analytics
    leaderboard.js        Top-scoring wallets
  components/             Shared UI components
  locales/                i18n (en, zh)
src/
  labels/                 Ground truth label fetching (Base only)
    fetch_virtuals.py     Virtuals ERC-6551 TBA addresses (Dune)
    fetch_acp.py          ACP-active wallet addresses (Dune)
    fetch_negatives.py    MEV bots, EOAs, CEX wallets (Dune + BaseScan)
    load_labels.py        Orchestrates all label fetching → Postgres
    sql/                  Dune SQL queries (01–07)
  features/               Feature engineering
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
```

## Current phase
**Deployed.** FastAPI backend + Next.js frontend live on Railway.
Live demo: https://agentry-frontend.onrender.com

Streamlit files removed. All dashboard pages are now Next.js.
Weekly sync cron (`sync.py`) runs on Railway to pull new Virtuals/ACP addresses.

## Conventions
- Keep all copy honest and non-exaggerated.
- Repo pushed to github.com/Amanda1005.
- Methodology transparency is a core differentiator vs Nansen/Arkham —
  document data sources, model, and limitations openly.

## Working style
Act as both a senior Web3 data scientist and a strict reviewer. Challenge
assumptions, flag unreliable data sources or methods, and verify facts by
searching the web rather than guessing. Do not agree just to please.
