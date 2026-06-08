# Week 3: Model training pipeline
# Run: python -m src.models.train
#
# Steps:
#   1. Load wallet_features + labels from Postgres
#   2. Random Forest baseline → ROC-AUC + recall@k
#   3. XGBoost → compare vs RF
#   4. SHAP feature importance
#
# Label encoding:
#   y=1  agent_virtuals, agent_acp      (known agents)
#   y=0  eoa_sampled, mev_bot           (reliable non-agents)
#
# Note: is_acp_participant excluded from features —
# it directly encodes label information (circular).

import numpy as np
import pandas as pd
import shap
import xgboost as xgb
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sqlalchemy import text

from src.db.models import get_engine, WalletFeatures

# ── Feature columns ────────────────────────────────────────────────────────────
FEATURE_COLS = [
    "transfer_total", "transfer_out", "transfer_in",
    "active_days", "active_hours", "hour_entropy",
    "weekend_ratio", "night_ratio", "inter_tx_cv", "burstiness",
    "unique_counterparties", "unique_tokens", "top_token_ratio",
]

# agent_virtuals excluded: ERC-6551 TBAs have zero on-chain behavioral signal
# (no ACP activity, minimal ERC-20 transfers) — model cannot learn to identify them.
# Documented as a known limitation; scored separately at inference time.
AGENT_LABELS = {"agent_acp"}


# ── Data loading ───────────────────────────────────────────────────────────────

def load_data() -> pd.DataFrame:
    """Load wallet_features joined with labels."""
    engine = get_engine()
    df = pd.read_sql(text("""
        SELECT wf.address, wf.transfer_total, wf.transfer_out, wf.transfer_in,
               wf.active_days, wf.active_hours, wf.hour_entropy,
               wf.weekend_ratio, wf.night_ratio, wf.inter_tx_cv, wf.burstiness,
               wf.unique_counterparties, wf.unique_tokens, wf.top_token_ratio,
               lw.label
        FROM wallet_features wf
        JOIN labeled_wallets lw ON wf.address = lw.address
    """), engine)
    df["y"] = df["label"].isin(AGENT_LABELS).astype(int)
    return df


# ── Evaluation helpers ─────────────────────────────────────────────────────────

def recall_at_k(y_true: pd.Series, y_score: np.ndarray, k: int) -> float:
    """Fraction of true positives captured in the top-k predictions."""
    top_idx = np.argsort(y_score)[::-1][:k]
    return float(y_true.iloc[top_idx].sum() / y_true.sum())


def print_metrics(name: str, y_true, y_score) -> None:
    auc = roc_auc_score(y_true, y_score)
    print(f"\n── {name} ──")
    print(f"  ROC-AUC : {auc:.4f}")
    for k in [50, 100, 200, 500]:
        if k <= len(y_true):
            r = recall_at_k(y_true, y_score, k)
            print(f"  recall@{k:<4}: {r:.3f}")


# ── Training ───────────────────────────────────────────────────────────────────

def train_rf(X_train, y_train) -> RandomForestClassifier:
    """Train Random Forest with median imputation for NaN."""
    imp = SimpleImputer(strategy="median")
    X_imp = imp.fit_transform(X_train)
    model = RandomForestClassifier(
        n_estimators=300,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_imp, y_train)
    model._imputer = imp   # store imputer for later use
    return model


def train_xgb(X_train, y_train) -> xgb.XGBClassifier:
    """Train XGBoost (handles NaN natively)."""
    scale = (y_train == 0).sum() / (y_train == 1).sum()
    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        scale_pos_weight=scale,   # handles class imbalance
        random_state=42,
        eval_metric="auc",
        verbosity=0,
    )
    model.fit(X_train, y_train)
    return model


# ── SHAP ───────────────────────────────────────────────────────────────────────

def shap_summary(model: xgb.XGBClassifier, X: pd.DataFrame) -> None:
    """Print top-10 features by mean |SHAP| value."""
    explainer   = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X.fillna(X.median()))
    mean_abs    = pd.Series(np.abs(shap_values).mean(axis=0), index=X.columns)
    print("\n── SHAP feature importance (XGBoost) ──")
    for feat, val in mean_abs.sort_values(ascending=False).head(10).items():
        print(f"  {feat:<30} {val:.4f}")


# ── Main ───────────────────────────────────────────────────────────────────────

def run():
    print("Loading data...")
    df = load_data()
    print(f"  {len(df)} wallets  |  agents: {df['y'].sum()}  |  non-agents: {(df['y']==0).sum()}")

    X = df[FEATURE_COLS]
    y = df["y"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )
    print(f"  Train: {len(X_train)}  |  Test: {len(X_test)}")

    # ── Random Forest ──────────────────────────────────────────────────────────
    print("\nTraining Random Forest...")
    rf = train_rf(X_train, y_train)
    rf_scores = rf.predict_proba(rf._imputer.transform(X_test))[:, 1]
    print_metrics("Random Forest", y_test, rf_scores)

    # ── XGBoost ────────────────────────────────────────────────────────────────
    print("\nTraining XGBoost...")
    xgb_model = train_xgb(X_train, y_train)
    xgb_scores = xgb_model.predict_proba(X_test)[:, 1]
    print_metrics("XGBoost", y_test, xgb_scores)

    # ── SHAP ───────────────────────────────────────────────────────────────────
    shap_summary(xgb_model, X_test)


def train_and_save(model_path: str = "models/xgb_base.json") -> xgb.XGBClassifier:
    """Train XGBoost on ALL labeled data and save to disk."""
    import os, joblib
    os.makedirs("models", exist_ok=True)

    df      = load_data()
    X, y    = df[FEATURE_COLS], df["y"]
    model   = train_xgb(X, y)
    model.save_model(model_path)
    print(f"Model saved → {model_path}")
    return model


def score_all_wallets(model_path: str = "models/xgb_base.json") -> None:
    """Score every wallet in wallet_features and write agent_score to DB."""
    from sqlalchemy.orm import Session
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    model = xgb.XGBClassifier()
    model.load_model(model_path)

    engine = get_engine()
    df     = load_data()
    X      = df[FEATURE_COLS]
    scores = (model.predict_proba(X)[:, 1] * 100).round(1)

    rows = [{"address": addr, "agent_score": float(s)}
            for addr, s in zip(df["address"], scores)]

    with Session(engine) as session:
        for row in rows:
            session.execute(
                pg_insert(WalletFeatures)
                .values(address=row["address"], agent_score=row["agent_score"])
                .on_conflict_do_update(
                    index_elements=["address"],
                    set_={"agent_score": row["agent_score"]},
                )
            )
        session.commit()
    print(f"Scored {len(rows)} wallets → wallet_features.agent_score")


if __name__ == "__main__":
    run()
