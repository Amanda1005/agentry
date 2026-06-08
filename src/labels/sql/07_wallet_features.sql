-- Week 2: aggregate behavioral features for labeled wallets
--
-- Source tables:
--   base.transactions                          (on-chain tx data)
--   dune.amandatw.dataset_labeled_wallets      (uploaded CSV: address, label)
--   ACP contract: 0x9c6c5a7125934cc6a711a7bf44f3cdcccf91f30c
--
-- Window: 90 days
-- Output: one row per wallet, all feature columns

WITH wallet_txs AS (
    SELECT
        t."from"                                                          AS address,
        t.block_time,
        t.gas_price,
        t.data,
        t."to"                                                            AS to_address,
        t."to" = 0x9c6c5a7125934cc6a711a7bf44f3cdcccf91f30c             AS is_acp_tx
    FROM base.transactions t
    INNER JOIN dune.amandatw.dataset_labeled_wallets w
        ON t."from" = w.address
    WHERE t.block_time > NOW() - INTERVAL '30' DAY
      AND t.success = true
),
top_method AS (
    -- Most-used function selector per wallet (repetitiveness signal)
    SELECT address, MAX(cnt) AS top_method_count
    FROM (
        SELECT
            address,
            bytearray_substring(data, 1, 4) AS method_sig,
            COUNT(*)                         AS cnt
        FROM wallet_txs
        WHERE LENGTH(data) >= 4
        GROUP BY 1, 2
    ) m
    GROUP BY 1
),
acp AS (
    SELECT
        t."from"    AS address,
        COUNT(*)    AS acp_tx_count
    FROM base.transactions t
    INNER JOIN dune.amandatw.dataset_labeled_wallets w
        ON t."from" = w.address
    WHERE t."to"        = 0x9c6c5a7125934cc6a711a7bf44f3cdcccf91f30c
      AND t.block_time  > NOW() - INTERVAL '90' DAY
      AND t.success     = true
    GROUP BY 1
)
SELECT
    lw.address,
    lw.label,

    -- Temporal
    COUNT(t.block_time)                                                          AS tx_count,
    COUNT(DISTINCT CAST(t.block_time AS DATE))                                   AS active_days,
    COUNT(DISTINCT hour(t.block_time))                                           AS active_hours,
    AVG(CASE WHEN day_of_week(t.block_time) IN (6, 7) THEN 1.0 ELSE 0.0 END)   AS weekend_ratio,
    AVG(CASE WHEN hour(t.block_time) < 6   THEN 1.0 ELSE 0.0 END)              AS night_ratio,

    -- Gas
    AVG(t.gas_price) / 1e9                                                      AS gas_price_mean_gwei,
    stddev_samp(t.gas_price) / 1e9                                              AS gas_price_std_gwei,
    CASE WHEN AVG(t.gas_price) > 0
         THEN stddev_samp(t.gas_price) / AVG(t.gas_price)
         ELSE NULL END                                                           AS gas_price_cv,

    -- Behavior
    AVG(CASE WHEN LENGTH(t.data) > 0 THEN 1.0 ELSE 0.0 END)                    AS contract_call_ratio,
    COUNT(DISTINCT t."to")                                                       AS unique_to_count,
    COALESCE(tm.top_method_count, 0) * 1.0
        / NULLIF(COUNT(t.block_time), 0)                                         AS top_method_ratio,

    -- ACP
    COALESCE(a.acp_tx_count, 0)                                                 AS acp_tx_count,
    COALESCE(a.acp_tx_count, 0) > 0                                             AS is_acp_participant

FROM dune.amandatw.dataset_labeled_wallets lw
LEFT JOIN wallet_txs t  ON lw.address = t.address
LEFT JOIN top_method tm ON lw.address = tm.address
LEFT JOIN acp        a  ON lw.address = a.address
GROUP BY lw.address, lw.label, tm.top_method_count, a.acp_tx_count
ORDER BY lw.label, lw.address
