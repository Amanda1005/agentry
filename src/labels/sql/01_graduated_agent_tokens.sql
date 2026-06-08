-- Step 1: Graduated Virtuals agent tokens on Base
--
-- Source contract: fun.virtuals.io launchpad
--   0xF66DeA7b3e897cD44A5a231c61B6B4423d613259
-- Graduation event topic0:
--   0x381d54fa425631e6266af114239150fae1d5db67bb65b4fa9ecc65013107e07e
--
-- Event structure:
--   topic1 = old_token (bonding-curve ERC-20, indexed)
--   data[0:32] = new_token (graduated ERC-20, non-indexed, ABI-padded)
--
-- Address extraction: ABI pads 20-byte addresses to 32 bytes (12 zero bytes + address).
-- substring(..., 13, 20) skips the 12 padding bytes and takes the 20-byte address.

SELECT
    bytearray_substring(data,   13, 20) AS new_token,   -- graduated token contract address
    bytearray_substring(topic1, 13, 20) AS old_token,   -- bonding-curve token (for traceability)
    block_time                          AS grad_time,
    tx_hash                             AS grad_tx
FROM base.logs
WHERE contract_address = 0xF66DeA7b3e897cD44A5a231c61B6B4423d613259
  AND topic0 = 0x381d54fa425631e6266af114239150fae1d5db67bb65b4fa9ecc65013107e07e
  AND block_time > CAST('2024-10-01' AS TIMESTAMP)
ORDER BY block_time DESC
-- Total as of 2026-06: ~400 rows
