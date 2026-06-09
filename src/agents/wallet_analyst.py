"""
Agentry Wallet Intelligence Analyst
Powered by Azure AI Foundry (GitHub Models endpoint) — Foundry IQ integration
"""

import os
from openai import OpenAI

FOUNDRY_IQ_KNOWLEDGE = """
# Agentry Knowledge Base — Agentic Wallet Behavior
Source: Foundry IQ / Agentry Research

## What is an Agentic Wallet?
An agentic wallet exhibits autonomous, automated on-chain behavior distinct from human-controlled
wallets. On-chain data cannot cleanly separate LLM-driven agents, MEV bots, protocol keepers, and
CEX automation — Agentry detects and scores *automated behavior*, validated against known AI agent
wallets from the Virtuals Protocol and ACP ecosystem.

## Behavioral Feature Reference

### Temporal Signals
- **active_days** (90-day window): Agents typically score 60–90 days. Humans: 5–30 days. The
  strongest single predictor — autonomous systems run continuously.
- **active_hours**: Distinct hours of day seen. Agents: 18–24 hours (24/7 coverage). Humans: 6–12.
- **inter_tx_cv**: Coefficient of variation of inter-transaction intervals. Low CV (< 0.5) =
  clockwork, machine-driven timing. High CV (> 2.0) = irregular, human-like randomness.
- **night_ratio**: Fraction of transactions 00–06 UTC. Agents: typically > 0.15 (never sleeps).
  Humans: usually < 0.05.
- **weekend_ratio**: Fraction on weekends. Agents: ~0.29 (flat across all 7 days). Humans: lower
  weekend engagement.

### Volume & Activity
- **transfer_total**: Total ERC-20 transfers in 90 days. Agents: 100–10,000+. Humans: 5–100.

### Network Diversity
- **unique_counterparties**: Distinct addresses interacted with. High diversity = agent executing
  a broad strategy (e.g., ACP message routing, liquidity provisioning).
- **unique_tokens**: Number of different tokens transacted. High = diversified automated strategy.
- **top_token_ratio**: Fraction of transfers in the most common token. Low (< 0.3) = diversified
  agent; High (> 0.8) = single-purpose bot or simple automation.

## Known Agent Types on Base (Ground Truth)
1. **Virtuals ERC-6551 TBAs**: Token Bound Accounts from the Virtuals Protocol — on-chain AI agent
   NFTs whose associated wallets execute autonomous transactions.
2. **ACP-active Wallets** (Agent Commerce Protocol): Wallets with ≥1,000 Memo events / 90 days,
   indicating active multi-agent communication and task delegation.

## Score Interpretation
- **70–100**: High-confidence agentic behavior. Automated agent, keeper, or bot.
- **40–69**: Uncertain. Power user, partially automated, or infrequent agent.
- **0–39**: Human-like. Irregular timing, limited 24/7 coverage.

## Methodological Caveats
- Positive-Unlabeled (PU) framing: low score = "not detected as agent," not "confirmed human."
- Model trained and validated on Base only; cross-chain scores are experimental.
- Cannot distinguish LLM agents from MEV bots, keepers, or CEX automation on-chain.
- Model: XGBoost, ROC-AUC 0.94, trained on 1,606 verified agent addresses.
"""


def analyze_wallet(address: str, chain: str, score_data: dict) -> dict:
    token = (
        os.environ.get("GITHUB_TOKEN")
        or os.environ.get("AGENT_HACKATHON_API_KEY")
        or os.environ.get("AZURE_AI_TOKEN")
    )
    if not token:
        raise ValueError("GITHUB_TOKEN not configured")

    client = OpenAI(
        base_url="https://models.inference.ai.azure.com",
        api_key=token,
    )

    score = score_data.get("agent_score", 0)
    features_block = _format_features(score_data)

    messages = [
        {
            "role": "system",
            "content": (
                "You are the Agentry Wallet Intelligence Analyst — an AI reasoning agent that "
                "identifies autonomous, agentic behavior in EVM blockchain wallets.\n\n"
                "Use the following knowledge base to ground every claim with evidence:\n\n"
                + FOUNDRY_IQ_KNOWLEDGE
                + "\n\nReason step-by-step. Cite specific feature values. Be concise and technical."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Analyze this wallet's agentic behavior.\n\n"
                f"**Address:** `{address[:10]}…{address[-6:]}`\n"
                f"**Chain:** {chain.capitalize()}\n"
                f"**Agent Score:** {score:.0f} / 100\n\n"
                f"**Behavioral Features:**\n{features_block}\n\n"
                "Respond in this exact structure:\n"
                "**1. Initial Assessment** — What does the score suggest?\n"
                "**2. Key Signals** — Which 2–3 features are most decisive and why?\n"
                "**3. Behavioral Pattern** — What type of automation does this resemble?\n"
                "**4. Caveats** — What limitations apply to this analysis?\n"
                "**5. Verdict** — One sentence conclusion."
            ),
        },
    ]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.2,
        max_tokens=700,
    )

    return {
        "analysis": response.choices[0].message.content,
        "powered_by": "Azure AI Foundry · gpt-4o-mini",
        "knowledge_source": "Agentry Foundry IQ Knowledge Base",
        "address": address,
        "chain": chain,
        "score": score,
    }


def _format_features(data: dict) -> str:
    specs = [
        ("active_days",           "Active Days (90d)",          None),
        ("active_hours",          "Active Hours",                None),
        ("transfer_total",        "Total Transfers",             None),
        ("night_ratio",           "Night Activity (00–06 UTC)",  "pct"),
        ("weekend_ratio",         "Weekend Activity",            "pct"),
        ("unique_counterparties", "Unique Counterparties",       None),
        ("unique_tokens",         "Unique Tokens",               None),
        ("top_token_ratio",       "Top Token Ratio",             "pct"),
        ("inter_tx_cv",           "Timing Regularity (CV)",      "f3"),
    ]
    lines = []
    for key, label, fmt in specs:
        val = data.get(key)
        if val is None:
            continue
        if fmt == "pct":
            val_str = f"{float(val) * 100:.1f}%"
        elif fmt == "f3":
            val_str = f"{float(val):.3f}"
        else:
            val_str = str(val)
        lines.append(f"- {label}: **{val_str}**")
    return "\n".join(lines)
