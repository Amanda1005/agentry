-- Negative controls: CEX hot wallets on Base
--
-- Source: Dune community labels (labels.addresses)
-- These wallets exhibit the opposite of agentic behavior:
-- large bulk transfers, fund aggregation, no protocol diversity.

SELECT DISTINCT
    address,
    name,
    category
FROM labels.addresses
WHERE blockchain = 'base'
  AND category   = 'cex'
ORDER BY name
