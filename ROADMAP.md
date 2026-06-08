# Agentry — 8-Week Roadmap

Single-developer, portfolio build. Base chain only. Validation and honest
framing are non-negotiable (see CLAUDE.md).

## Week 1 — Labels & data foundation
- Positive labels: known agent wallets (Virtuals / ElizaOS) on Base; filter to active.
- Negative controls: known CEX hot wallets, known MEV bots, sampled active EOAs.
- Wire up primary data source (Dune).
- Output: a `labeled_wallets` table (address, chain=base, label, source).
- Do NOT model or build dashboard yet.

## Week 2 — Data pipeline + thin vertical slice
- For each wallet, pull a fixed 90-day snapshot of tx, transfers, contract interactions.
- Land in Postgres. Schema: wallets / transactions / interactions / labels.
- Goal: one wallet → features → a number → shown in a barebones Streamlit page.
- Cache fetched data; do not re-query Dune.

## Week 3 — Feature engineering
- Temporal (inter-tx interval regularity, hour-of-day entropy, 24/7 coverage, burstiness)
- Gas patterns, protocol diversity vs repetition, counterparty patterns
- x402 / ACP interaction flags
- contract-call vs simple-transfer ratio, sequence repetitiveness

## Week 4 — Modeling
- Frame as Positive-Unlabeled (PU) learning.
- Supervised classifier (gradient boosting / RF) + Isolation Forest for exploration.
- Calibrated agent-likelihood score (0–100). SHAP for explainability.

## Week 5 — Validation + LLM layer
- Hold out known agents; report recall@k / ranking; show negative controls score low; document limitations.
- LLM (not chatbot): agent dossiers, SHAP-paired plain-language explanations, optional agent-type classification.

## Week 6 — Dashboard (part 1)
1. Ecosystem Overview  2. Wallet Profiler (score + SHAP + LLM dossier)  3. Agent Leaderboard

## Week 7 — Dashboard (part 2) + graph
4. Behavioral Clusters  5. Network / counterparty graph (networkx)  6. Methodology page

## Week 8 — Polish, deploy, story
- Deploy (Streamlit Community Cloud / Render). README with methodology + limitations + results.
- 2–3 min demo video. LinkedIn post (practitioner framing).

## If behind, cut in this order
Network Graph page → LLM agent-type classification → Isolation Forest line → Clusters page.

## Never cut
The labeled dataset, the validation numbers, the Methodology page. These are the project's core.