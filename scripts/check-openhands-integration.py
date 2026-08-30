#!/usr/bin/env python3
"""Deterministic OpenHands integration smoke for Agent Bounties.

Stdlib only: the pinned verifier sandbox is a vanilla CPython image and cannot
pip-install PyCryptodome. This check covers the bounty acceptance criteria:

  * current OpenHands skill at .agents/skills/agent-bounties/SKILL.md
  * stop hook that blocks completion until tests and submission evidence exist
  * one exact next action for claimable, unfunded, verifier-unready, and
    submitted-not-paid
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".agents/skills/agent-bounties/SKILL.md"
HOOKS = ROOT / ".openhands/hooks.json"
GUARD = ROOT / ".openhands/hooks/agent-bounties-evidence.py"
FIXTURE_DIR = ROOT / "integrations/openhands/fixtures"
REQUIRED_STATES = (
    "claimable",
    "unfunded",
    "verifier-unready",
    "submitted-not-paid",
)
FEED = "https://api.agentbounties.app/v1/base/autonomous-bounties/feed"


def fail(msg: str) -> None:
    raise SystemExit(msg)


def main() -> None:
    skill = SKILL.read_text(encoding="utf-8")
    if not skill.startswith("---\n"):
        fail("skill missing YAML frontmatter")
    lower = skill.lower()
    for phrase in (
        "canonical",
        "claimable",
        "bountysettled",
        "one exact next action",
        "post your own bounty",
    ):
        if phrase not in lower:
            fail(f"skill missing {phrase}")
    if "label:bounty" in lower and "not" not in lower:
        fail("skill must not treat label:bounty as claimability evidence")

    hooks = json.loads(HOOKS.read_text(encoding="utf-8"))
    stop_hooks = hooks.get("stop")
    if not isinstance(stop_hooks, list) or not stop_hooks:
        fail("OpenHands integration requires a stop hook")
    encoded = json.dumps(stop_hooks, sort_keys=True)
    if ".openhands/hooks/agent-bounties-evidence" not in encoded:
        fail("stop hook does not invoke the Agent Bounties evidence guard")

    guard = GUARD.read_text(encoding="utf-8")
    for phrase in ("submission", "evidence", "test", "decision", "deny"):
        if phrase not in guard.lower():
            fail(f"evidence guard is missing {phrase}")
    for forbidden in ("private_key", "seed phrase", "eth_sendtransaction"):
        if forbidden in (skill + guard).lower():
            fail(f"forbidden wallet behavior: {forbidden}")

    seen_actions: set[str] = set()
    for state in REQUIRED_STATES:
        path = FIXTURE_DIR / f"{state}.json"
        if not path.is_file():
            fail(f"missing fixture {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        action = data.get("next_action")
        if not isinstance(action, str) or len(action.strip()) < 20:
            fail(f"{path} needs a concrete next_action string")
        if action in seen_actions:
            fail("each fixture must have a distinct next_action")
        seen_actions.add(action)
        al = action.lower()
        if state == "claimable" and "claim" not in al:
            fail("claimable next_action must direct a claim")
        if state == "unfunded" and "skip" not in al and "do not" not in al:
            fail("unfunded next_action must block premature work")
        if state == "verifier-unready" and "skip" not in al:
            fail("verifier-unready next_action must skip")
        if state == "submitted-not-paid":
            if "bountysettled" not in al.replace(" ", "") and "$0.00" not in al:
                fail("submitted-not-paid next_action must wait for BountySettled")

    # Guard with no configured claim state must allow (unrelated session).
    completed = subprocess.run(
        [sys.executable, str(GUARD)],
        cwd=ROOT,
        input="{}",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=15,
        check=False,
    )
    if completed.returncode not in (0, 2):
        fail(f"evidence guard unexpected exit {completed.returncode}: {completed.stdout[-1500:]}")

    print("check-openhands-integration: ok")
    print(f"fixtures={','.join(REQUIRED_STATES)}")
    print(f"canonical_feed={FEED}")


if __name__ == "__main__":
    main()
