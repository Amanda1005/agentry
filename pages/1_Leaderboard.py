"""Agentry — Leaderboard page"""

import pandas as pd
import streamlit as st
from sqlalchemy import text

from src.db.models import get_engine
from src.utils.nav import nav_bar

st.set_page_config(page_title="Agentry · Leaderboard", page_icon="⬡", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;900&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
.block-container { padding: 0 2rem 2rem 2rem !important; max-width: 1200px !important; }

.section-label {
    font-size: 11px; font-weight: 600; letter-spacing: 3px;
    text-transform: uppercase; color: #2563eb; margin-bottom: 8px;
}
.stat-card {
    background: #ffffff; border: 1px solid #e2e8f0;
    border-radius: 12px; padding: 20px 24px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.stat-num { font-size: 36px; font-weight: 800; color: #2563eb; }
.stat-label { font-size: 11px; color: #94a3b8; margin-top: 4px; letter-spacing: 1px; text-transform: uppercase; }

.hr { border: none; border-top: 1px solid #e2e8f0; margin: 40px 0; }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    engine = get_engine()
    return pd.read_sql(text("""
        SELECT lw.address, lw.label, wf.agent_score,
               wf.transfer_total, wf.active_days, wf.active_hours,
               wf.unique_counterparties, wf.inter_tx_cv
        FROM labeled_wallets lw
        LEFT JOIN wallet_features wf ON lw.address = wf.address AND lw.chain = wf.chain
        WHERE lw.chain = 'base'
        ORDER BY wf.agent_score DESC NULLS LAST
    """), engine)


df = load_data()
pct    = (df["agent_score"].fillna(0) >= 50).mean() * 100
n_high = int((df["agent_score"].fillna(0) >= 80).sum())


nav_bar(active="leaderboard")

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
st.markdown('<div class="section-label">Base Chain · Validated</div>', unsafe_allow_html=True)
st.markdown("<div style='font-size:40px; font-weight:900; color:#0f172a; margin-bottom:8px;'>Agent Leaderboard</div>", unsafe_allow_html=True)
st.markdown("<div style='font-size:15px; color:#64748b; margin-bottom:32px;'>Highest-scoring wallets on Base — ground truth validated.</div>", unsafe_allow_html=True)


# ── STATS ─────────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
cards = [
    (f"{len(df):,}",   "Wallets Analyzed"),
    (f"{pct:.0f}%",    "Show Agentic Behavior"),
    (f"{n_high:,}",    "High-Confidence Agents"),
    ("0.94",           "Model ROC-AUC"),
]
for col, (num, lbl) in zip([c1, c2, c3, c4], cards):
    col.markdown(f"""
    <div class="stat-card">
        <div class="stat-num">{num}</div>
        <div class="stat-label">{lbl}</div>
    </div>""", unsafe_allow_html=True)

st.markdown('<div class="hr"></div>', unsafe_allow_html=True)


# ── LEADERBOARD ───────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Top Agents</div>', unsafe_allow_html=True)
st.markdown("<div style='font-size:24px; font-weight:800; color:#0f172a; margin-bottom:16px;'>Highest scoring wallets</div>", unsafe_allow_html=True)

top = (
    df[df["agent_score"] >= 50]
    .nlargest(50, "agent_score")
    [["address", "label", "agent_score", "transfer_total", "active_days", "active_hours", "unique_counterparties"]]
    .reset_index(drop=True)
)
top.index += 1
top["address"] = top["address"].str[:10] + "..." + top["address"].str[-8:]
top.columns = ["Address", "Label", "Score", "Transfers", "Active Days", "Active Hours", "Counterparties"]

st.dataframe(top, use_container_width=True, height=600)
