# OpenHands earning-loop integration (slim artifact)

Minimal source snapshot for Agent Bounties issue #773 / contract
`0x294cda5faa1b1a9dd7eca2cb52daff1fa843ad22`.

Contains the files the immutable OpenHands benchmark reads at workspace root:

- `.agents/skills/agent-bounties/SKILL.md`
- `.openhands/hooks.json`
- `.openhands/hooks/agent-bounties-evidence.py`
- `integrations/openhands/fixtures/{claimable,unfunded,verifier-unready,submitted-not-paid}.json`
- `scripts/check-openhands-integration.py`

The stop hook blocks completion reporting until focused tests and submission
evidence exist. Each fixture emits one exact next action. Only a canonical
on-chain `BountySettled` event proves payment.

```
python scripts/check-openhands-integration.py
WORKSPACE_ROOT=. python /path/to/pinned/openhands-integration/check.py
```
