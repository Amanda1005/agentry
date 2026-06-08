-- Negative controls: MEV bots on Base
--
-- Heuristic: wallets that appear as BOTH sender and receiver of swaps
-- within the same block >= N times (sandwich pattern), OR wallets labeled
-- as MEV/arbitrage in Dune community labels.
--
-- Two-pronged approach:
--   A) Dune labels (fast, may have limited Base coverage)
--   B) Behavioral: high-frequency same-block swap senders (slow, used as fallback)
--
-- Behavioral heuristic: senders with high tx density per block over 7 days.
-- avg_txs_per_block > 5 AND total tx > 500 = strong automated/MEV signal.
-- Confirmed non-timeout on Base (2026-06).
--
-- Note: captures MEV bots, keeper bots, bundlers — all valid negatives
-- since none are Virtuals-style AI agents.

SELECT
    "from"                                        AS address,
    COUNT(*)                                      AS tx_count,
    COUNT(DISTINCT block_number)                  AS blocks_touched,
    COUNT(*) / COUNT(DISTINCT block_number)       AS avg_txs_per_block
FROM base.transactions
WHERE block_time > NOW() - INTERVAL '7' DAY
  AND success = true
GROUP BY 1
HAVING COUNT(*) > 500
   AND COUNT(*) / COUNT(DISTINCT block_number) > 5
ORDER BY tx_count DESC
LIMIT 200
