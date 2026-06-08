# Fetch ERC-20 transfer history via Alchemy alchemy_getAssetTransfers API.
# Results cached in Postgres raw_transfers — re-runs skip already-fetched wallets.
#
# Free tier: 330M CU/month. 3,351 wallets × 2 calls × 150 CU ≈ 1M CU total.

import time
import logging
from datetime import datetime, timezone

import requests
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import text

from src.config import ALCHEMY_API_KEY
from src.db.models import RawTransfer, FetchStatus, get_engine

log = logging.getLogger(__name__)

ALCHEMY_ENDPOINTS = {
    "base":      f"https://base-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}",
    "ethereum":  f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}",
    "polygon":   f"https://polygon-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}",
    "arbitrum":  f"https://arb-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}",
    "optimism":  f"https://opt-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}",
}
ALCHEMY_URL = ALCHEMY_ENDPOINTS["base"]   # default for backward compatibility
DELAY       = 0.05   # 20 req/sec (free tier allows much more, conservative)


def _get_page(address: str, direction: str, page_key: str | None, chain: str = "base") -> dict:
    url = ALCHEMY_ENDPOINTS.get(chain, ALCHEMY_URL)
    params: dict = {
        "fromBlock":        "0x0",
        "toBlock":          "latest",
        "category":         ["erc20"],
        "withMetadata":     True,
        "excludeZeroValue": False,
        "maxCount":         "0x3e8",   # 1000 per page
    }
    if direction == "from":
        params["fromAddress"] = address
    else:
        params["toAddress"] = address
    if page_key:
        params["pageKey"] = page_key

    resp = requests.post(
        url,
        json={"id": 1, "jsonrpc": "2.0", "method": "alchemy_getAssetTransfers", "params": [params]},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _fetch_direction(address: str, direction: str, chain: str = "base", max_pages: int = 5) -> list[dict]:
    all_txs, page_key, pages = [], None, 0
    while pages < max_pages:
        data = _get_page(address, direction, page_key, chain)
        if "error" in data:
            raise RuntimeError(f"Alchemy error: {data['error']}")
        result   = data.get("result", {})
        all_txs.extend(result.get("transfers", []))
        page_key = result.get("pageKey")
        pages   += 1
        if not page_key:
            break
        time.sleep(DELAY)
    return all_txs


def _to_row(wallet: str, tx: dict, chain: str = "base") -> dict:
    ts = tx.get("metadata", {}).get("blockTimestamp", "")
    return {
        "wallet_address": wallet.lower(),
        "chain":          chain,
        "block_number":   int(tx["blockNum"], 16),
        "block_time":     datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else None,
        "tx_hash":        tx["hash"].lower(),
        "from_address":   (tx.get("from") or "").lower(),
        "to_address":     (tx.get("to")   or "").lower(),
        "token_address":  (tx.get("rawContract", {}).get("address") or "").lower(),
        "token_symbol":   (tx.get("asset") or "")[:50],
        "value_raw":      (tx.get("rawContract", {}).get("value") or "0")[:80],
    }


def _fetch_one(addr: str, chain: str = "base") -> tuple[str, list[dict]]:
    """Fetch all transfers for one address (both directions). Returns (addr, rows)."""
    txs = _fetch_direction(addr, "from", chain) + _fetch_direction(addr, "to", chain)
    return addr, [_to_row(addr, t, chain) for t in txs]


def fetch_all_wallets(addresses: list[str], chain: str = "base", workers: int = 10) -> None:
    """Fetch ERC-20 transfers for all addresses in parallel; skip cached ones."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    engine = get_engine()

    with Session(engine) as s:
        done = {r[0] for r in s.execute(
            text("SELECT address FROM fetch_status WHERE chain = :chain"),
            {"chain": chain},
        ).fetchall()}

    todo = [a for a in addresses if a.lower() not in done]
    print(f"[{chain}] To fetch: {len(todo)}  |  Already cached: {len(done)}  |  Workers: {workers}")

    completed = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_fetch_one, addr, chain): addr for addr in todo}
        for fut in as_completed(futures):
            addr = futures[fut]
            try:
                _, rows = fut.result()
                with Session(engine) as s:
                    if rows:
                        s.execute(pg_insert(RawTransfer).values(rows).on_conflict_do_nothing())
                    s.execute(
                        pg_insert(FetchStatus)
                        .values(address=addr.lower(), chain=chain, transfer_count=len(rows))
                        .on_conflict_do_nothing()
                    )
                    s.commit()
            except Exception as e:
                log.warning(f"  ✗ {addr}: {e}")

            completed += 1
            if completed % 100 == 0:
                print(f"  [{chain}] {completed}/{len(todo)} done")

    print(f"[{chain}] Fetch complete.")
