# inventory-state-breakdown-v1

Slim source snapshot for NSPG13/agent-bounties#870
(`0x22cec92c195a6dc0f7aeaf850e7f2cacb3b6de33`).

`scripts/check-inventory-state-breakdown.py` derives ready_to_earn,
in_progress, submitted, paid, and verification_unavailable from one
canonical snapshot. Strict ready-to-earn filtering is unchanged.
Degraded and stale projections never promote unsafe contracts.

`site/home-inventory-breakdown.js` consumes the same counts on the
homepage without relabeling claimed or unverified work as ready.
