from sqlalchemy import (
    create_engine, Column, String, DateTime,
    Float, Integer, Boolean, Text, BigInteger, UniqueConstraint,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func
from src.config import DATABASE_URL

Base = declarative_base()


class LabeledWallet(Base):
    __tablename__ = "labeled_wallets"

    address = Column(String(42), primary_key=True)
    chain   = Column(String(20), primary_key=True, nullable=False, default="base")
    label = Column(String(50), nullable=False)      # e.g. agent_virtuals, cex_hot_wallet, mev_bot, eoa_sampled
    label_source = Column(String(100), nullable=False)  # e.g. virtuals_agent_factory, basescan_label
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RawTransfer(Base):
    """ERC-20 transfer records fetched via Alchemy, cached per wallet+chain."""
    __tablename__ = "raw_transfers"
    __table_args__ = (
        UniqueConstraint("wallet_address", "chain", "tx_hash", "token_address", "from_address", "to_address",
                         name="raw_transfers_wallet_chain_unique"),
    )

    id            = Column(BigInteger, primary_key=True, autoincrement=True)
    wallet_address = Column(String(42), nullable=False, index=True)
    chain         = Column(String(20), nullable=False, default="base")
    block_number  = Column(BigInteger)
    block_time    = Column(DateTime(timezone=True))
    tx_hash       = Column(String(66))
    from_address  = Column(String(42))
    to_address    = Column(String(42))
    token_address = Column(String(42))
    token_symbol  = Column(String(50))
    value_raw     = Column(String(80))
    fetched_at    = Column(DateTime(timezone=True), server_default=func.now())


class FetchStatus(Base):
    """Tracks which wallets have been fetched per chain (skip re-fetch)."""
    __tablename__ = "fetch_status"

    address        = Column(String(42), primary_key=True)
    chain          = Column(String(20), primary_key=True, nullable=False, default="base")
    transfer_count = Column(Integer, default=0)
    fetched_at     = Column(DateTime(timezone=True), server_default=func.now())


class WalletFeatures(Base):
    __tablename__ = "wallet_features"

    address     = Column(String(42), primary_key=True)
    chain       = Column(String(20), primary_key=True, nullable=False, default="base")
    window_days = Column(Integer, nullable=False, default=90)
    computed_at = Column(DateTime(timezone=True), server_default=func.now())

    # Transfer volume
    transfer_total  = Column(Integer)
    transfer_out    = Column(Integer)
    transfer_in     = Column(Integer)

    # Temporal
    active_days     = Column(Integer)
    active_hours    = Column(Integer)
    hour_entropy    = Column(Float)
    weekend_ratio   = Column(Float)
    night_ratio     = Column(Float)
    inter_tx_cv     = Column(Float)
    burstiness      = Column(Float)

    # Counterparty / token diversity
    unique_counterparties = Column(Integer)
    unique_tokens         = Column(Integer)
    top_token_ratio       = Column(Float)

    # ACP
    is_acp_participant    = Column(Boolean, default=False)

    # Model output
    agent_score           = Column(Float)   # 0–100, XGBoost predicted probability × 100


class CrossChainScore(Base):
    """Agent scores for wallets across EVM chains (non-Base)."""
    __tablename__ = "cross_chain_scores"
    __table_args__ = (
        UniqueConstraint("address", "chain"),
    )

    id              = Column(BigInteger, primary_key=True, autoincrement=True)
    address         = Column(String(42), nullable=False, index=True)
    chain           = Column(String(20), nullable=False)
    agent_score     = Column(Float)
    transfer_total  = Column(Integer)
    active_days     = Column(Integer)
    active_hours    = Column(Integer)
    night_ratio     = Column(Float)
    weekend_ratio   = Column(Float)
    unique_counterparties = Column(Integer)
    unique_tokens   = Column(Integer)
    top_token_ratio = Column(Float)
    inter_tx_cv     = Column(Float)
    computed_at     = Column(DateTime(timezone=True), server_default=func.now())


def get_engine():
    return create_engine(DATABASE_URL)


def create_tables():
    engine = get_engine()
    Base.metadata.create_all(engine)
