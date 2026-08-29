#!/usr/bin/env python3
"""inventory-state-breakdown-v1 — truthful counts from one canonical snapshot.

Derives ready_to_earn, in_progress, submitted, paid, and
verification_unavailable from a single accepted projection. Strict
ready-to-earn filtering is unchanged: only claimable + verification_ready
items from a fresh, non-degraded source count as ready. Claimed work is
never relabeled ready. Source degradation is reported, not papered over.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "inventory-state-breakdown-v1"
MAX_AGE_SECONDS = 900
ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "scripts" / "fixtures" / "inventory-state-breakdown"
FIXTURES = ("empty", "mixed", "degraded", "stale")

READY_STATUSES = {"claimable"}
IN_PROGRESS_STATUSES = {"claimed"}
SUBMITTED_STATUSES = {"submitted", "verifying"}
PAID_STATUSES = {"paid"}


def parse_generated_at(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        stamp = datetime.fromisoformat(text)
    except ValueError:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp.astimezone(timezone.utc)


def source_info(snapshot: dict) -> dict:
    source = snapshot.get("source")
    if not isinstance(source, dict):
        source = {}
    available = bool(source.get("available", True))
    degraded = bool(source.get("degraded", False)) or not available
    reason = source.get("degradation_reason")
    if degraded and not reason:
        reason = "source unavailable" if not available else "source marked degraded"
    return {
        "available": available,
        "degraded": degraded,
        "degradation_reason": reason,
        "kind": source.get("kind") or "canonical_projection",
        "url": source.get("url"),
        "safe_block": source.get("safe_block"),
        "indexed_at": source.get("indexed_at"),
    }


def item_status(item: dict) -> str:
    status = str(item.get("status") or item.get("source_status") or "").strip().lower()
    work = str(item.get("work_state") or "").strip().lower()
    payment = str(item.get("payment_state") or "").strip().lower()
    if payment == "paid" or status == "paid":
        return "paid"
    if status in SUBMITTED_STATUSES or work == "submitted":
        return "submitted"
    if status in IN_PROGRESS_STATUSES or work == "in_progress":
        return "in_progress"
    if status in READY_STATUSES or work == "claimable":
        return "claimable"
    return status or "unknown"


def is_strict_ready(item: dict) -> bool:
    """Keep strict ready-to-earn filtering unchanged."""
    if item_status(item) != "claimable":
        return False
    if item.get("verification_ready") is not True:
        return False
    if item.get("terms_valid") is False:
        return False
    if str(item.get("work_state") or "claimable").strip().lower() not in {"", "claimable"}:
        return False
    return True


def breakdown(snapshot: dict, *, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    generated_at = parse_generated_at(snapshot.get("generated_at"))
    src = source_info(snapshot)
    items = snapshot.get("items") if isinstance(snapshot.get("items"), list) else []
    age = None if generated_at is None else (now - generated_at).total_seconds()
    stale = generated_at is None or age is None or age < 0 or age > MAX_AGE_SECONDS

    ready = in_progress = submitted = paid = unverified = 0
    for raw in items:
        if not isinstance(raw, dict):
            unverified += 1
            continue
        bucket = item_status(raw)
        if bucket == "paid":
            paid += 1
        elif bucket == "submitted":
            submitted += 1
        elif bucket == "in_progress":
            in_progress += 1
        elif bucket == "claimable":
            if src["degraded"] or stale:
                unverified += 1
            elif is_strict_ready(raw):
                ready += 1
            else:
                unverified += 1
        else:
            unverified += 1

    return {
        "schema": SCHEMA,
        "generated_at": snapshot.get("generated_at"),
        "source": src,
        "stale": stale,
        "age_seconds": None if age is None else int(age),
        "ready_to_earn": 0 if src["degraded"] or stale else ready,
        "in_progress": in_progress,
        "submitted": submitted,
        "paid": paid,
        "verification_unavailable": unverified if not (src["degraded"] and ready == 0 and unverified == 0) else unverified,
        "item_count": len(items),
        "source_degraded": src["degraded"],
        "source_degradation_reason": src["degradation_reason"],
        "safe_block": src["safe_block"],
    }


def load_fixture(name: str) -> dict:
    path = FIXTURE_DIR / f"{name}.json"
    if not path.is_file():
        raise SystemExit(f"missing fixture {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    failures = []
    for name in FIXTURES:
        fixture = load_fixture(name)
        expected = fixture.get("expected")
        if not isinstance(expected, dict):
            failures.append(f"{name}: missing expected counts")
            continue
        now = parse_generated_at(fixture.get("observed_at")) or datetime.now(timezone.utc)
        got = breakdown(fixture["snapshot"], now=now)
        for key in (
            "ready_to_earn",
            "in_progress",
            "submitted",
            "paid",
            "verification_unavailable",
        ):
            if got.get(key) != expected.get(key):
                failures.append(
                    f"{name}: {key} got {got.get(key)} expected {expected.get(key)}"
                )
        if bool(got["stale"]) != bool(expected.get("stale", name == "stale")):
            failures.append(f"{name}: stale flag {got['stale']} expected {expected.get('stale')}")
        if bool(got["source_degraded"]) != bool(expected.get("source_degraded", name == "degraded")):
            failures.append(
                f"{name}: source_degraded {got['source_degraded']} expected {expected.get('source_degraded')}"
            )
        print(json.dumps({"fixture": name, "breakdown": got}, sort_keys=True))
    if failures:
        print("inventory-state-breakdown-v1 failures:", file=sys.stderr)
        for line in failures:
            print(f"  {line}", file=sys.stderr)
        return 1
    print("inventory-state-breakdown-v1 fixtures passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
