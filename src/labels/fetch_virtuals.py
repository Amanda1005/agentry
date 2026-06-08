# Week 1: fetch Virtuals Protocol agent wallet addresses from Dune.
#
# Two complementary queries:
#   1. Graduated agent tokens (fun.virtuals.io bonding curve graduates)
#      → Dune query 7642088  |  SQL: 01_graduated_agent_tokens.sql
#   2. ERC-6551 TBA addresses for all Virtuals NFT agents
#      → Dune query TBD      |  SQL: 02_virtuals_agent_tbas.sql
#
# Contracts:
#   Launchpad:        0xF66DeA7b3e897cD44A5a231c61B6B4423d613259  (fun.virtuals.io)
#   Virtuals NFT:     0x50725af160260a316b2673c71c8c21469f6732c0  (ERC-721)
#   ERC-6551 Registry:0x000000006551c19487814612e58FE06813775758  (standard)

from src.utils.dune_client import run_query

GRADUATED_TOKENS_QUERY_ID = 7642088
VIRTUALS_TBA_QUERY_ID = 7656386  # https://dune.com/queries/7656386


def fetch_graduated_tokens() -> list[dict]:
    """Fetch graduated Virtuals agent token addresses (~400 rows).

    Returns: list of dicts with keys: new_token, old_token, grad_time, grad_tx
    """
    return run_query(GRADUATED_TOKENS_QUERY_ID)


def fetch_virtuals_tbas() -> list[dict]:
    """Fetch ERC-6551 TBA wallet addresses for all Virtuals agents (~1220 rows).

    Returns: list of dicts with keys: tba_address, token_id_raw, created_at
    """
    if VIRTUALS_TBA_QUERY_ID is None:
        raise RuntimeError("Save sql/02_virtuals_agent_tbas.sql to Dune and set VIRTUALS_TBA_QUERY_ID.")
    return run_query(VIRTUALS_TBA_QUERY_ID)
