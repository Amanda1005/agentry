-- ACP-active agent wallets on Base
--
-- Source: ACP contract (0x9c6c5a7125934cc6a711a7bf44f3cdcccf91f30c)
-- Event: Memo event (topic0 = 0xbb0268ad...)
-- topic3 = ABI-padded address of the ACP participant (receiver/counterparty)
--
-- Threshold >= 1000 memos = high-confidence automated behavior.
-- Note: some addresses may be ERC-4337 smart contract wallets, not EOAs.
-- Label these as 'agent_acp', NOT 'agent_virtuals' — ACP is an open protocol
-- used beyond just Virtuals agents.
--
-- Total wallets >= 1000: ~1,606

SELECT
    bytearray_substring(topic3, 13, 20) AS agent_wallet,
    COUNT(*)                            AS memo_count
FROM base.logs
WHERE contract_address = 0x9c6c5a7125934cc6a711a7bf44f3cdcccf91f30c
  AND topic0 = 0xbb0268ad77b327d705a64b3c848fabb951ad3ae3485bbb4c0a1aac688669a15a
GROUP BY 1
HAVING COUNT(*) >= 1000
ORDER BY 2 DESC
