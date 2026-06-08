-- Step 2: Virtuals Protocol agent ERC-6551 TBA wallet addresses on Base
--
-- Source: Standard ERC-6551 Registry (0x000000006551c19487814612e58FE06813775758)
-- Event: AccountCreated(address account, address indexed implementation,
--                       uint256 chainId, address indexed tokenContract,
--                       uint256 indexed tokenId, uint256 salt)
--
-- Virtuals NFT contract (ERC-721): 0x50725af160260a316b2673c71c8c21469f6732c0
-- Filtering topic2 = Virtuals NFT contract isolates only Virtuals agent TBAs.
--
-- TBA address is the first non-indexed param, ABI-padded to 32 bytes in data.
-- bytearray_substring(data, 13, 20) skips 12 zero-padding bytes → 20-byte address.
--
-- Total as of 2026-06: ~1,220 TBAs

SELECT
    bytearray_substring(data, 13, 20) AS tba_address,
    topic3                            AS token_id_raw,
    block_time                        AS created_at
FROM base.logs
WHERE contract_address = 0x000000006551c19487814612e58fe06813775758
  AND topic0 = 0x79f19b3655ee38b1ce526556b7731a20c8f218fbda4a3990b6cc4172fdf88722
  AND topic2 = 0x00000000000000000000000050725af160260a316b2673c71c8c21469f6732c0
ORDER BY block_time DESC
