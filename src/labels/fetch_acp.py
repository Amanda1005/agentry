# Week 1: fetch ACP-active agent wallet addresses from Dune.
#
# Source: ACP Memo event on contract 0x9c6c5a7125934cc6a711a7bf44f3cdcccf91f30c
# Threshold: >= 1000 memos = high-confidence automated behavior
# Label: agent_acp (NOT agent_virtuals — ACP is an open protocol)
#
# Dune query 7656414: https://dune.com/queries/7656414
# SQL: src/labels/sql/03_agent_acp.sql
# ~1,606 wallets as of 2026-06

from src.utils.dune_client import run_query

AGENT_ACP_QUERY_ID = 7656414


def fetch_acp_agents() -> list[dict]:
    """Fetch ACP-active wallet addresses with >= 1000 memos (~1,606 rows).

    Returns: list of dicts with keys: agent_wallet, memo_count
    """
    return run_query(AGENT_ACP_QUERY_ID)
