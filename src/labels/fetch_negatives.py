# Week 1: fetch negative-control wallet addresses.
#
# CEX hot wallets: BaseScan labeled addresses (category = "exchange")
#   Dune community labels have zero CEX coverage on Base — use BaseScan API instead.
#
# MEV bots + random EOAs: fetched via Dune (see sql/05 and sql/06).
#   Save those SQL files as Dune queries and fill in the query IDs below.

import requests
from src.config import BASESCAN_API_KEY
from src.utils.dune_client import run_query

MEV_QUERY_ID  = 7656416  # https://dune.com/queries/7656416
EOA_QUERY_ID  = 7656448  # https://dune.com/queries/7656448

BASESCAN_LABELS_URL = "https://api.etherscan.io/v2/api"


def fetch_cex_wallets() -> list[dict]:
    """Fetch CEX hot wallet addresses from BaseScan labeled accounts page.

    BaseScan labels exchange addresses; this pages through the results.
    Returns list of dicts with keys: address, name.
    """
    params = {
        "module":  "account",
        "action":  "getlabels",
        "tag":     "exchange",
        "apikey":  BASESCAN_API_KEY,
    }
    resp = requests.get(BASESCAN_LABELS_URL, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != "1":
        raise RuntimeError(f"BaseScan API error: {data.get('message')} — {data.get('result')}")
    return [{"address": r["address"].lower(), "name": r["name"]} for r in data["result"]]


def fetch_mev_bots() -> list[dict]:
    """Fetch MEV / high-frequency bot addresses from Dune (behavioral heuristic).

    Returns list of dicts with keys: address, tx_count, avg_txs_per_block.
    """
    if MEV_QUERY_ID is None:
        raise RuntimeError("Save sql/05_negative_mev.sql to Dune and set MEV_QUERY_ID.")
    return run_query(MEV_QUERY_ID)


def fetch_eoa_sample() -> list[dict]:
    """Fetch randomly sampled active EOA addresses from Dune.

    Returns list of dicts with keys: address, tx_count.
    """
    if EOA_QUERY_ID is None:
        raise RuntimeError("Save sql/06_negative_eoa_sample.sql to Dune and set EOA_QUERY_ID.")
    return run_query(EOA_QUERY_ID)
