# Agentry — Agentic Wallet Observatory

Score any EVM wallet 0–100 for autonomous, agent-like behavior.  
Validated on Base · Experimental on Ethereum, Arbitrum, Optimism, Polygon.

**Live demo →** _coming soon_

---

## What it does

Agentry detects wallets that exhibit *agentic / automated behavior* on EVM chains — regular timing patterns, 24/7 activity, high counterparty diversity, repetitive token flows — and scores them 0–100.

**Honest framing:** On-chain data cannot cleanly separate LLM-driven agents, MEV bots, trading automation, and protocol keepers. Agentry detects and scores *automated behavior*, validated against known AI agent wallets. It does not definitively identify "AI agents."

---

## Why it's different

| | Nansen / Arkham | Agentry |
|---|---|---|
| Labels known entities (CEXs, whales) | ✅ | ❌ |
| Scores for AI agent / automated behavior | ❌ | ✅ |
| Trained on verified agent ground truth | ❌ | ✅ (1,606 wallets) |
| Methodology transparent + SHAP explanations | ❌ | ✅ |
| Open limitations documentation | ❌ | ✅ |

---

## Use cases

- **Airdrop protection** — filter automated wallets before token distribution
- **Protocol analytics** — measure what % of your DeFi activity is human vs automated
- **Agent discovery** — find the most active AI agents in the Virtuals / ACP ecosystem

---

## Model

| Property | Value |
|---|---|
| Algorithm | XGBoost binary classifier |
| ROC-AUC | **0.94** (held-out test set) |
| Training data | Base mainnet, 90-day ERC-20 transfer history |
| Positive labels | Virtuals ERC-6551 TBAs + ACP-active wallets (~1,606) |
| Negative labels | ~70 MEV bots + 1,000 sampled EOAs |
| Learning framing | Positive-Unlabeled (PU) — unlabeled ≠ negative |
| Explainability | SHAP feature importance per wallet |

**Top predictive features (SHAP):** `active_days` › `inter_tx_cv` › `transfer_total`

### Chain coverage

| Chain | Status | Notes |
|---|---|---|
| Base | ✅ Validated | Model trained + validated here |
| Ethereum, Arbitrum, Optimism, Polygon | ⚡ Experimental | Base model applied cross-chain, not independently validated |

---

## Behavioral features

Derived from 90-day ERC-20 transfer history:

| Feature | What it captures |
|---|---|
| `active_days` | How many distinct days the wallet transacted |
| `active_hours` | How many distinct hours of day seen |
| `inter_tx_cv` | Regularity of transaction timing (low CV = clockwork) |
| `night_ratio` | Fraction of activity between 00–06 UTC |
| `weekend_ratio` | Fraction of activity on weekends |
| `transfer_total` | Total number of ERC-20 transfers |
| `unique_counterparties` | Breadth of wallet interactions |
| `unique_tokens` | Token diversity |
| `top_token_ratio` | Concentration in a single token |

---

## Tech stack

- **Backend:** FastAPI + SQLAlchemy + Postgres
- **ML:** XGBoost, scikit-learn, SHAP
- **Data:** Dune Analytics (ground truth labels), Alchemy (live wallet features)
- **Frontend:** Next.js
- **Analytics dashboard:** Streamlit
- **Deploy:** Railway (API + weekly sync cron)

---

## Architecture

```
Dune Analytics ──► labeled_wallets (Postgres)
                         │
Alchemy RPC ─────► wallet_features (Postgres)
                         │
                   xgb_base.json ──► /api/score
                         │
                    Next.js frontend
```

Weekly cron (`sync.py`) pulls new Virtuals / ACP addresses from Dune, fetches their features via Alchemy, and scores them — no model retraining.

---

## Run locally

**Prerequisites:** Python 3.11+, Node 18+, Postgres

```bash
# 1. Clone and install
git clone https://github.com/Amanda1005/agentry
cd agentry
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Environment
cp .env.example .env
# Fill in: DATABASE_URL, ALCHEMY_API_KEY, DUNE_API_KEY

# 3. Backend API
uvicorn api:app --reload --port 8000

# 4. Frontend
cd frontend && npm install && npm run dev
# → http://localhost:3000

# 5. (Optional) Streamlit analytics dashboard
cd .. && streamlit run app.py
# → http://localhost:8501
```

---

## Known limitations

- Model trained and validated on Base only. Non-Base scores are experimental and unvalidated.
- ~15% of EOA "negatives" may be unlabeled agents — inherent to PU learning.
- 90-day behavioral window: inactive or new wallets score near zero regardless of type.
- Cannot distinguish LLM-driven agents from MEV bots or trading automation.
- ACP participation flag is Base-only; cross-chain scoring lacks this signal.

---

## Project structure

```
api.py                    FastAPI backend
app.py                    Streamlit analytics dashboard
sync.py                   Weekly incremental data sync (Railway cron)
models/xgb_base.json      Trained XGBoost model
src/
  labels/                 Ground truth label fetching (Dune)
  features/               Feature engineering (Alchemy)
  models/train.py         Model training + SHAP
  db/models.py            SQLAlchemy ORM
frontend/                 Next.js frontend
pages/                    Streamlit sub-pages
```

---

## Data sources

| Source | Used for |
|---|---|
| [Virtuals Protocol](https://app.virtuals.io) | ERC-6551 TBA addresses (positive labels) |
| ACP (Agent Commerce Protocol) | Active agent wallet addresses (positive labels) |
| Dune Analytics | Label queries, cached in Postgres |
| Alchemy | ERC-20 transfer history per wallet |
| BaseScan | MEV bot addresses (negative labels) |

---

*Methodology transparency is a core differentiator. All data sources, model decisions, and limitations are documented openly.*
