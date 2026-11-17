"""Bonus B3: swarm_verified keeps the swarm, adds a code verifier before the write."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bonus.swarm_verified import run_claim as swarm_verified
from lab8.config_loader import repo_path
from lab8.db import connect, init_store, load_json, load_jsonl
from lab8.durability import InjectedCrash
from lab8.shapes import SHAPES
from tests.conftest import CLAIMS, WORLD

BONUS_WORLD = load_json(repo_path("bonus", "world.json"))
BONUS_CLAIMS = load_jsonl(repo_path("bonus", "cases.jsonl"))
BONUS_BY_ID = {row["claim_id"]: row for row in BONUS_CLAIMS}


def _public_store(tmp_path, name: str) -> str:
    path = tmp_path / name
    init_store(path, WORLD, CLAIMS).close()
    return str(path)


def _bonus_store(tmp_path, name: str) -> str:
    path = tmp_path / name
    init_store(path, BONUS_WORLD, BONUS_CLAIMS).close()
    return str(path)


def _events(result, kind: str) -> list[dict]:
    body = json.loads(Path(result.trace_path).read_text(encoding="utf-8"))
    return [event["payload"] for event in body["events"] if event["kind"] == kind]


def _ledger(store: str, claim_id: str) -> int:
    conn = connect(store)
    try:
        row = conn.execute("SELECT COALESCE(SUM(amount_vnd), 0) AS s FROM refund_ledger WHERE claim_id = ?", (claim_id,)).fetchone()
        return int(row["s"])
    finally:
        conn.close()


def test_verifier_blocks_overstated_delay_c002_seed55(tmp_path):
    """Public T02: ticket 5 days, order 2. Swarm pays on seed 55; the verifier re-quotes to 0."""
    swarm = SHAPES["swarm"]("C-002", seed=55, store_path=_public_store(tmp_path, "s.sqlite"))
    store = _public_store(tmp_path, "v.sqlite")
    verified = swarm_verified("C-002", seed=55, store_path=store)

    assert swarm.status == "resolved"
    assert verified.status == "denied"
    assert verified.proposal_amount == 0
    assert _ledger(store, "C-002") == 0
    overrides = _events(verified, "verifier_override")
    assert len(overrides) == 1
    assert overrides[0]["fields"] == ["delay_days"]
    assert overrides[0]["amount_before"] == 20000 and overrides[0]["amount_after"] == 0


def test_verifier_restores_understated_delay_b02_seed55(tmp_path):
    """Ticket says 1 day, order says 5: the swarm denies on seed 55, the verifier pays the fee."""
    store = _bonus_store(tmp_path, "b02.sqlite")
    result = swarm_verified("B-02", seed=55, store_path=store)
    assert result.status == "resolved"
    assert result.proposal_amount == 30000
    assert _ledger(store, "B-02") == 30000
    assert len(_events(result, "verifier_override")) == 1


@pytest.mark.parametrize("claim_id", [row["claim_id"] for row in CLAIMS])
def test_same_as_swarm_when_no_override(tmp_path, claim_id):
    """Seed 11 never triggers the swarm weakness: the variant must decide exactly like the swarm."""
    swarm = SHAPES["swarm"](claim_id, seed=11, store_path=_public_store(tmp_path, "s.sqlite"))
    verified = swarm_verified(claim_id, seed=11, store_path=_public_store(tmp_path, "v.sqlite"))
    assert (verified.status, verified.proposal_amount) == (swarm.status, swarm.proposal_amount)
    assert verified.refund_effects == swarm.refund_effects
    assert verified.model_calls == swarm.model_calls
    assert _events(verified, "verifier_override") == []


def test_override_logged_even_when_amount_unchanged_b05(tmp_path):
    """Ticket cites another order's 9 days first; the shipping fee is the same either way."""
    result = swarm_verified("B-05", seed=55, store_path=_bonus_store(tmp_path, "b05.sqlite"))
    assert result.status == "resolved"
    assert result.proposal_amount == 35000
    [override] = _events(result, "verifier_override")
    assert override["amount_before"] == override["amount_after"] == 35000


def test_crash_then_resume_keeps_one_refund(tmp_path):
    store = _public_store(tmp_path, "crash.sqlite")
    with pytest.raises(InjectedCrash):
        swarm_verified("C-012", seed=11, store_path=store, crash_at="after_effect_before_checkpoint")
    result = swarm_verified("C-012", seed=11, store_path=store)
    assert result.status == "resolved"
    assert result.committed_audit_count == 1
    conn = connect(store)
    try:
        assert conn.execute("SELECT COUNT(*) AS n FROM refund_ledger WHERE claim_id = 'C-012'").fetchone()["n"] == 1
    finally:
        conn.close()


def test_host_reason_from_stored_status_is_not_echoed(tmp_path):
    store = _public_store(tmp_path, "status.sqlite")
    conn = connect(store)
    with conn:
        conn.execute("UPDATE approvals SET status = 'CANARY_SECRET_STATUS' WHERE approval_id = 'A-001'")
    conn.close()
    result = swarm_verified("C-001", seed=11, store_path=store)
    assert result.status == "denied"
    assert result.error_reason == "policy_denied"
    assert "CANARY_SECRET" not in str(result.as_dict())
    assert "CANARY_SECRET" not in Path(result.trace_path).read_text(encoding="utf-8")


def test_bonus_cases_are_hand_labelled():
    """Every adversarial case carries a written reason for its label (no generated labels)."""
    assert len(BONUS_CLAIMS) >= 8
    for row in BONUS_CLAIMS:
        assert row["label_note"].strip(), row["claim_id"]
        assert {"status", "proposal_amount", "refund_vnd", "refund_count", "audit_refund_committed"} <= row["expected"].keys()
