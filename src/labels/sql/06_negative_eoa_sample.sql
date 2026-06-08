-- Negative controls: randomly sampled active human-proxy EOAs on Base
--
-- Strategy:
--   1. Take senders from recent Base transactions (last 90 days)
--   2. Keep only addresses with 5–200 txs (active but not machine-like)
--   3. Exclude known contracts, CEX wallets, and our positive-label addresses
--   4. Randomly sample ~500 addresses
--
-- Caveat: "random EOA" != "pure human". Some will be unlabeled bots.
-- This is inherent to PU learning — treat these as the "unlabeled" pool,
-- not as confirmed negatives. Document this clearly.

-- Note: base.transactions."from" is always an EOA or ERC-4337 account —
-- regular contracts cannot appear as the sender. No need to filter against
-- base.creation_traces (396M rows; would timeout).
-- labels.addresses exclusion removes known DEX pools, DAOs, bridges etc.

WITH active_senders AS (
    SELECT
        "from"   AS address,
        COUNT(*) AS tx_count
    FROM base.transactions
    WHERE block_time > NOW() - INTERVAL '90' DAY
      AND success = true
    GROUP BY 1
    HAVING COUNT(*) BETWEEN 5 AND 200
),
known_labels AS (
    SELECT DISTINCT address
    FROM labels.addresses
    WHERE blockchain = 'base'
)
SELECT
    s.address,
    s.tx_count
FROM active_senders s
LEFT JOIN known_labels k ON s.address = k.address
WHERE k.address IS NULL
ORDER BY RAND()
LIMIT 500
