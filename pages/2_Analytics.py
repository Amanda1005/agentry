"""Agentry — Analytics page"""

import pandas as pd
import altair as alt
import streamlit as st
from sqlalchemy import text

from src.db.models import get_engine
from src.utils.nav import nav_bar

st.set_page_config(page_title="Agentry · Analytics", page_icon="⬡", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;900&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
.block-container { padding: 0 2rem 2rem 2rem !important; max-width: 1200px !important; }

.section-label {
    font-size: 11px; font-weight: 600; letter-spacing: 3px;
    text-transform: uppercase; color: #2563eb; margin-bottom: 8px;
}
.uc-card {
    background: #ffffff; border: 1px solid #e2e8f0;
    border-radius: 12px; padding: 24px; height: 100%;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.uc-num { font-size: 11px; font-weight: 600; color: #2563eb; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 12px; }
.uc-title { font-size: 20px; font-weight: 700; color: #0f172a; margin-bottom: 8px; }
.uc-desc { font-size: 14px; color: #64748b; line-height: 1.5; }

.hr { border: none; border-top: 1px solid #e2e8f0; margin: 40px 0; }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    engine = get_engine()
    return pd.read_sql(text("""
        SELECT lw.address, lw.label, wf.agent_score
        FROM labeled_wallets lw
        LEFT JOIN wallet_features wf ON lw.address = wf.address AND lw.chain = wf.chain
        WHERE lw.chain = 'base'
        ORDER BY wf.agent_score DESC NULLS LAST
    """), engine)


df = load_data()


nav_bar(active="analytics")

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
st.markdown('<div class="section-label">Base Chain · Model Analytics</div>', unsafe_allow_html=True)
st.markdown("<div style='font-size:40px; font-weight:900; color:#0f172a; margin-bottom:8px;'>Score Distribution</div>", unsafe_allow_html=True)
st.markdown("<div style='font-size:15px; color:#64748b; margin-bottom:32px;'>How the model separates agents from non-agents on Base.</div>", unsafe_allow_html=True)


# ── DISTRIBUTION CHART ────────────────────────────────────────────────────────
hist = (
    df.dropna(subset=["agent_score"])
    .assign(bin=lambda d: (d["agent_score"] // 5 * 5).astype(int))
    .groupby(["bin", "label"]).size().reset_index(name="count")
)
color_map = {
    "agent_acp":      "#2563eb",
    "agent_virtuals": "#60a5fa",
    "eoa_sampled":    "#f87171",
    "mev_bot":        "#fb923c",
}
chart = (
    alt.Chart(hist).mark_bar(opacity=0.9, cornerRadiusTopLeft=2, cornerRadiusTopRight=2)
    .encode(
        x=alt.X("bin:Q", title="Agent Score", scale=alt.Scale(domain=[0, 100])),
        y=alt.Y("count:Q", title="Wallets"),
        color=alt.Color("label:N",
            scale=alt.Scale(domain=list(color_map.keys()), range=list(color_map.values())),
            legend=alt.Legend(orient="top")),
        tooltip=["label", "bin", "count"],
    )
    .properties(height=380)
    .configure_view(strokeWidth=0, fill="#ffffff")
    .configure_axis(gridColor="#f1f5f9", domainColor="#e2e8f0", labelColor="#94a3b8", titleColor="#64748b")
    .configure_legend(labelColor="#475569", titleColor="#64748b", labelFontSize=12)
)
st.altair_chart(chart, use_container_width=True)

st.markdown('<div class="hr"></div>', unsafe_allow_html=True)


# ── USE CASES ─────────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Use Cases</div>', unsafe_allow_html=True)
st.markdown("<div style='font-size:28px; font-weight:800; color:#0f172a; margin-bottom:24px;'>What you can do with Agentry</div>", unsafe_allow_html=True)

u1, u2, u3 = st.columns(3)
use_cases = [
    ("USE CASE 01", "Airdrop Protection",
     "Filter bot wallets before your airdrop. Wallets scoring ≥70 are likely automated protect token distribution fairness."),
    ("USE CASE 02", "Protocol Analytics",
     "Understand your real user base. Know what % of your DeFi protocol's activity comes from humans vs automated agents."),
    ("USE CASE 03", "Agent Discovery",
     "Find the most active AI agents on Base. Track which wallets in the Virtuals/ACP ecosystem generate real on-chain activity."),
]
for col, (num, title, desc) in zip([u1, u2, u3], use_cases):
    col.markdown(f"""
    <div class="uc-card">
        <div class="uc-num">{num}</div>
        <div class="uc-title">{title}</div>
        <div class="uc-desc">{desc}</div>
    </div>""", unsafe_allow_html=True)

st.markdown('<div class="hr"></div>', unsafe_allow_html=True)


# ── METHODOLOGY ───────────────────────────────────────────────────────────────
with st.expander("Methodology & Limitations"):
    st.markdown("""
    **Model:** XGBoost binary classifier — ROC-AUC **0.94** on held-out test set.

    **Positive labels:** Virtuals ERC-6551 TBAs + ACP-active wallets (~1,606 total, Base)
    **Negative labels:** ~70 MEV bots + 1,000 random EOAs (Base)

    **Behavioral features** derived from 90-day ERC-20 transfer history:
    active days, transfer volume, night / weekend ratios, counterparty diversity,
    token concentration, interval regularity (CV).

    **Top predictive features (SHAP):** `active_days` › `inter_tx_cv` › `transfer_total`

    **Known limitations:**
    - Model trained and validated on Base only. Non-Base chain scores are experimental.
    - ~15% of EOA "negatives" may be unlabeled agents (inherent PU learning problem).
    - 90-day behavioral window; inactive wallets score near zero regardless of type.
    - Cannot distinguish LLM-driven agents from MEV bots or trading automation — detects
      *agentic behavior*, not definitively "AI agents."

    *This tool scores automated behavior likelihood — not definitive AI agent identification.*
    """)
