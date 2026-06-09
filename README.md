# Agentry — Agentic Wallet Observatory

> **Microsoft Agents League Hackathon 2026 · Reasoning Agents Track**  
> Integrates **Azure AI Foundry (Foundry IQ)** for grounded, cited wallet intelligence.

Score any EVM wallet 0–100 for autonomous, agent-like behavior.  
Validated on Base · Experimental on Ethereum, Arbitrum, Optimism, Polygon.

**Live demo →** https://agentry-frontend.onrender.com

---

## What it does

Agentry is a reasoning agent that detects wallets exhibiting *agentic / automated behavior* on EVM chains — regular timing, 24/7 activity, high counterparty diversity, repetitive token flows — and scores them 0–100.

After scoring, an **Azure AI Foundry-powered AI Analyst** reasons step-by-step through the behavioral evidence, citing the Agentry Foundry IQ knowledge base to explain *why* a wallet received its score.

**Honest framing:** On-chain data cannot cleanly separate LLM-driven agents, MEV bots, trading automation, and protocol keepers. Agentry detects and scores *automated behavior*, validated against known AI agent wallets. It does not definitively identify "AI agents."

---

## Microsoft IQ Integration — Foundry IQ

**Track:** Reasoning Agents  
**IQ Layer:** Foundry IQ (Azure AI Foundry · GitHub Models endpoint)

| Component | Implementation |
|---|---|
| **Knowledge retrieval** | Foundry IQ knowledge base embedded in agent context — protocols (ERC-6551, Virtuals, ACP), feature thresholds, behavioral patterns |
| **Grounded answers** | Every explanation cites specific feature values vs. known agent thresholds |
| **Cited reasoning** | 5-step structured analysis: assessment → signals → pattern → caveats → verdict |
| **Model** | gpt-4o-mini via `https://models.inference.ai.azure.com` (Azure AI Foundry endpoint) |
| **Agent endpoint** | `GET /api/analyze?address=<addr>&chain=<chain>` |

### Architecture

```
User enters wallet address
        │
        ▼
┌─────────────────────┐
│   Next.js Frontend  │
└─────────┬───────────┘
          │ /api/score
          ▼
┌─────────────────────┐     ┌──────────────────────┐
│   FastAPI Backend   │────►│  Postgres (cached     │
│                     │     │  wallet_features)     │
│  XGBoost Classifier │     └──────────────────────┘
│  (ROC-AUC 0.94)     │
└─────────┬───────────┘
          │ /api/analyze
          ▼
┌──────────────────────────────────────────────┐
│         Azure AI Foundry Agent               │
│  ┌──────────────────────────────────────┐    │
│  │  Foundry IQ Knowledge Base           │    │
│  │  • ERC-6551 / Virtuals / ACP docs    │    │
│  │  • Feature threshold reference       │    │
│  │  • Known agent behavioral patterns   │    │
│  └──────────────────────────────────────┘    │
│  Model: gpt-4o-mini (GitHub Models endpoint) │
└──────────────────────────────────────────────┘
          │
          ▼
  5-step grounded analysis with citations
```

---

## Why it's different

| | Nansen / Arkham | Agentry |
|---|---|---|
| Labels known entities (CEXs, whales) | ✅ | ❌ |
| Scores for AI agent / automated behavior | ❌ | ✅ |
| Trained on verified agent ground truth | ❌ | ✅ (1,606 wallets) |
| SHAP + AI-explained reasoning | ❌ | ✅ |
| Azure AI Foundry Foundry IQ grounding | ❌ | ✅ |
| Open methodology documentation | ❌ | ✅ |

---

## Use cases

- **Airdrop protection** — filter automated wallets before token distribution
- **Protocol analytics** — measure what % of your DeFi activity is human vs automated
- **Agent discovery** — find the most active AI agents in the Virtuals / ACP ecosystem
- **On-chain agent auditing** — grounded AI explanation of any wallet's behavioral profile

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
| Explainability | SHAP feature importance + Foundry IQ AI analysis |

**Top predictive features (SHAP):** `active_days` › `inter_tx_cv` › `transfer_total`

### Chain coverage

| Chain | Status | Notes |
|---|---|---|
| Base | ✅ Validated | Model trained + validated here |
| Ethereum, Arbitrum, Optimism, Polygon | ⚡ Experimental | Base model applied cross-chain |

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
- **AI Agent:** Azure AI Foundry (GitHub Models) · gpt-4o-mini · Foundry IQ knowledge retrieval
- **Data:** Dune Analytics (ground truth labels), Alchemy (live wallet features)
- **Frontend:** Next.js (i18n: English / 中文)
- **Deploy:** Railway (API + weekly sync cron)

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
# Required: DATABASE_URL, ALCHEMY_API_KEY, DUNE_API_KEY
# For AI analysis: GITHUB_TOKEN (fine-grained PAT with Models: Read permission)
#   → github.com → Settings → Developer settings → Fine-grained tokens → Models: Read

# 3. Backend API
uvicorn api:app --reload --port 8000

# 4. Frontend
cd frontend && npm install && npm run dev
# → http://localhost:3000
```

---

## API endpoints

| Endpoint | Description |
|---|---|
| `GET /api/score?address=&chain=` | Score a wallet (XGBoost) |
| `GET /api/analyze?address=&chain=` | AI reasoning analysis (Azure AI Foundry) |
| `GET /api/leaderboard` | Top-scoring Base wallets |
| `GET /api/distribution` | Score distribution by label |
| `GET /api/stats` | Aggregate stats |

---

## Known limitations

- Model trained and validated on Base only. Non-Base scores are experimental.
- ~15% of EOA "negatives" may be unlabeled agents — inherent to PU learning.
- 90-day behavioral window: inactive or new wallets score near zero.
- Cannot distinguish LLM-driven agents from MEV bots or trading automation.
- ACP participation flag is Base-only; cross-chain scoring lacks this signal.

---

## Project structure

```
api.py                    FastAPI backend (scoring + AI analysis endpoints)
sync.py                   Weekly incremental data sync (Railway cron)
models/xgb_base.json      Trained XGBoost model
src/
  agents/
    wallet_analyst.py     Azure AI Foundry agent (Foundry IQ integration)
  labels/                 Ground truth label fetching (Dune)
  features/               Feature engineering (Alchemy)
  models/train.py         Model training + SHAP
  db/models.py            SQLAlchemy ORM
frontend/                 Next.js frontend (i18n: en, zh)
  pages/index.js          Wallet scorer + AI analysis panel
  pages/analytics.js      Score distribution
  pages/leaderboard.js    Top agents
```

---

## Data sources

| Source | Used for |
|---|---|
| [Virtuals Protocol](https://app.virtuals.io) | ERC-6551 TBA addresses (positive labels) |
| ACP (Agent Commerce Protocol) | Active agent wallet addresses (positive labels) |
| Dune Analytics | Label queries, cached in Postgres |
| Alchemy | ERC-20 transfer history per wallet |
| Azure AI Foundry (GitHub Models) | Foundry IQ grounded wallet analysis |

---

*Methodology transparency is a core differentiator. All data sources, model decisions, and limitations are documented openly.*
