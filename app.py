"""
Agentry — Agentic Wallet Observatory
Run: streamlit run app.py
"""

import pandas as pd
import streamlit as st
import xgboost as xgb
from sqlalchemy import text

from src.db.models import get_engine
from src.features.fetch_transfers import _fetch_direction
from src.features.compute_features import compute
from src.models.train import FEATURE_COLS
from src.utils.nav import nav_bar

st.set_page_config(page_title="Agentry", page_icon="⬡", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;900&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
.block-container { padding: 0 2rem 2rem 2rem !important; max-width: 1200px !important; }
/* Ensure radio buttons inherit background */
div[data-testid="stRadio"] { background: transparent !important; }

.section-label {
    font-size: 11px; font-weight: 600; letter-spacing: 3px;
    text-transform: uppercase; color: #2563eb; margin-bottom: 8px;
}
.hero-title {
    font-size: 52px; font-weight: 900; line-height: 1.1; color: #0f172a; margin: 0;
}
.hero-title span { color: #2563eb; }
.hero-sub { font-size: 16px; color: #64748b; margin-top: 12px; max-width: 540px; line-height: 1.6; }

.stat-card {
    background: #ffffff; border: 1px solid #e2e8f0;
    border-radius: 12px; padding: 20px 24px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.stat-num { font-size: 36px; font-weight: 800; color: #2563eb; }
.stat-label { font-size: 11px; color: #94a3b8; margin-top: 4px; letter-spacing: 1px; text-transform: uppercase; }

.score-card { border-radius: 16px; padding: 32px 24px; text-align: center; }
.score-big { font-size: 80px; font-weight: 900; line-height: 1; }
.score-label-sm { font-size: 11px; color: #94a3b8; letter-spacing: 3px; text-transform: uppercase; margin-top: 6px; }
.verdict { font-size: 18px; font-weight: 700; margin-top: 16px; }

.hr { border: none; border-top: 1px solid #e2e8f0; margin: 40px 0; }

.pill { display:inline-block; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.pill-green  { background: #dcfce7; color: #16a34a; }
.pill-red    { background: #fee2e2; color: #dc2626; }
.pill-yellow { background: #fef9c3; color: #ca8a04; }
.pill-gray   { background: #f1f5f9; color: #64748b; }
</style>
""", unsafe_allow_html=True)

CHAINS = ["Base", "Ethereum", "Arbitrum", "Optimism", "Polygon"]
CHAIN_KEY = {"Base": "base", "Ethereum": "ethereum", "Arbitrum": "arbitrum",
             "Optimism": "optimism", "Polygon": "polygon"}


# ── Data & Model ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_base_scores() -> pd.DataFrame:
    engine = get_engine()
    return pd.read_sql(text("""
        SELECT lw.address, lw.label, wf.agent_score,
               wf.transfer_total, wf.active_days, wf.active_hours,
               wf.night_ratio, wf.weekend_ratio, wf.unique_counterparties,
               wf.unique_tokens, wf.top_token_ratio, wf.inter_tx_cv
        FROM labeled_wallets lw
        LEFT JOIN wallet_features wf ON lw.address = wf.address AND lw.chain = wf.chain
        WHERE lw.chain = 'base'
        ORDER BY wf.agent_score DESC NULLS LAST
    """), engine)


@st.cache_data(ttl=300)
def load_cross_chain(chain_key: str) -> pd.DataFrame:
    engine = get_engine()
    return pd.read_sql(text("""
        SELECT address, agent_score, transfer_total, active_days, active_hours,
               night_ratio, weekend_ratio, unique_counterparties,
               unique_tokens, top_token_ratio, inter_tx_cv
        FROM cross_chain_scores WHERE chain = :chain
        ORDER BY agent_score DESC NULLS LAST
    """), engine, params={"chain": chain_key})


@st.cache_resource
def load_model():
    m = xgb.XGBClassifier()
    m.load_model("models/xgb_base.json")
    return m


def score_live(address: str, chain_key: str = "base") -> dict | None:
    txs = _fetch_direction(address, "from", chain_key) + _fetch_direction(address, "to", chain_key)
    if not txs:
        return None
    from datetime import datetime
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
    import pandas as _pd
    df_w = _pd.DataFrame(rows)
    df_w["block_time"] = _pd.to_datetime(df_w["block_time"], utc=True)
    feat = compute(df_w, address)
    if feat is None:
        return {"agent_score": 0.0}
    X = _pd.DataFrame([{c: feat.get(c) for c in FEATURE_COLS}]).astype(float)
    score = float(load_model().predict_proba(X)[:, 1][0]) * 100
    feat["agent_score"] = round(score, 1)
    return feat


nav_bar(active="home")

# ── HERO ──────────────────────────────────────────────────────────────────────
st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)
st.markdown("""
<div class="section-label">Multi-Chain · Behavioral Intelligence</div>
<div class="hero-title">Detect AI Agent Behavior<br>in <span>On-Chain Wallets</span></div>
<div class="hero-sub">
  Score any wallet 0–100 for autonomous behavior.
  Validated on Base · Experimental on other EVM chains.
</div>
""", unsafe_allow_html=True)

st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)


# ── CHAIN SELECTOR + WALLET EXPLORER ─────────────────────────────────────────
st.markdown('<div class="section-label">Wallet Explorer</div>', unsafe_allow_html=True)
st.markdown("<div style='font-size:28px; font-weight:800; color:#0f172a; margin-bottom:16px;'>Score any wallet for AI agent behavior</div>", unsafe_allow_html=True)

chain_col, _ = st.columns([3, 5])
with chain_col:
    chain_name = st.radio("Chain", CHAINS, horizontal=True, label_visibility="collapsed")

chain_key = CHAIN_KEY[chain_name]
is_base = chain_key == "base"

if is_base:
    st.markdown("<div style='font-size:13px; color:#64748b; margin-bottom:16px;'>Base results are model-validated · Known wallets load instantly</div>", unsafe_allow_html=True)
else:
    st.markdown(f"<div style='font-size:13px; color:#f59e0b; margin-bottom:16px;'>⚠ {chain_name} — scored with Base-trained model · Experimental, not independently validated</div>", unsafe_allow_html=True)

query = st.text_input("", placeholder="0x...", label_visibility="collapsed")

if query and query.strip():
    q = query.strip().lower()

    if is_base:
        df_base = load_base_scores()
        match = df_base[df_base["address"].str.lower() == q]
        if match.empty:
            with st.spinner("Fetching on-chain data…"):
                result = score_live(q, "base")
            if result is None:
                st.error(f"No transfer activity found for this address on {chain_name}.")
                st.stop()
            score, label, feat_src = result.get("agent_score", 0), "unknown", result
        else:
            row = match.iloc[0]
            score, label, feat_src = row["agent_score"] or 0, row["label"], row.to_dict()
    else:
        df_cc = load_cross_chain(chain_key)
        match = df_cc[df_cc["address"].str.lower() == q]
        if match.empty:
            with st.spinner(f"Fetching on-chain data from {chain_name}…"):
                result = score_live(q, chain_key)
            if result is None:
                st.error(f"No transfer activity found for this address on {chain_name}.")
                st.stop()
            score, label, feat_src = result.get("agent_score", 0), "unknown", result
        else:
            row = match.iloc[0]
            score, label, feat_src = row["agent_score"] or 0, "unknown", row.to_dict()

    color    = "#2563eb" if score >= 70 else "#f59e0b" if score >= 40 else "#ef4444"
    bg_color = "#eff6ff" if score >= 70 else "#fffbeb" if score >= 40 else "#fef2f2"
    verdict  = "🤖 AGENT" if score >= 70 else "⚠️ UNCERTAIN" if score >= 40 else "👤 HUMAN"
    pill_cls = "pill-green" if score >= 70 else "pill-yellow" if score >= 40 else "pill-red"

    col1, col2 = st.columns([1, 2])
    with col1:
        experimental_badge = "" if is_base else '<div style="margin-top:8px;font-size:10px;color:#f59e0b;">Experimental · Base model</div>'
        st.markdown(f"""
        <div class="score-card" style="background:{bg_color}; border:1px solid {color}30;">
            <div class="score-big" style="color:{color};">{score:.0f}</div>
            <div class="score-label-sm">Agent Score · {chain_name}</div>
            <div class="verdict" style="color:#0f172a;">{verdict}</div>
            <div style="margin-top:8px;"><span class="pill {pill_cls}">{label}</span></div>
            {experimental_badge}
            <div style="margin-top:8px; font-size:11px; color:#94a3b8;">{q[:22]}...</div>
        </div>""", unsafe_allow_html=True)

    with col2:
        st.markdown("<div style='font-size:16px; font-weight:600; color:#0f172a; margin-bottom:12px;'>Behavioral Fingerprint</div>", unsafe_allow_html=True)
        features = {
            "Active Days (90d)":          feat_src.get("active_days") or 0,
            "Active Hours":               feat_src.get("active_hours") or 0,
            "Total Transfers":            feat_src.get("transfer_total") or 0,
            "Night Activity (00–06 UTC)": f"{(feat_src.get('night_ratio') or 0)*100:.1f}%",
            "Weekend Activity":           f"{(feat_src.get('weekend_ratio') or 0)*100:.1f}%",
            "Unique Counterparties":      feat_src.get("unique_counterparties") or 0,
            "Unique Tokens":              feat_src.get("unique_tokens") or 0,
            "Top Token Ratio":            f"{(feat_src.get('top_token_ratio') or 0)*100:.1f}%",
            "Interval CV":                f"{feat_src.get('inter_tx_cv') or 0:.2f}",
        }
        fdf = pd.DataFrame(list(features.items()), columns=["Feature", "Value"])
        st.dataframe(fdf, use_container_width=True, hide_index=True, height=340)
