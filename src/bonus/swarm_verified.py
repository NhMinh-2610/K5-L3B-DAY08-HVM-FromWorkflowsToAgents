"""Bonus B3 — swarm reference plus a code verifier before the refund write.

The swarm part is the reference swarm, step for step: same peer/parse/draft model calls,
same handoff and investigators, and the same REFERENCE_WEAKNESS (on seed % 5 == 0 it
trusts a delay number written in the ticket). The only addition is `verify()`:

    Before deciding, re-read the order through the read tool (independent of every
    agent), compare each fact used to quote (delay_days, status, damage_verified) with
    the structured row, and if any differs, re-quote from the structured row. One repair
    round at most. The override is written to the trace as `verifier_override`.

One deliberate safety change versus the reference: host denial reasons are filtered
through the same allowlist as the workflow shape, because the host builds some
reasons from stored data (approval_<status>).

Run next to swarm and workflow (from src/):

    python -m lab8.benchmark --shapes workflow,swarm,swarm_verified \
        --extra-shape swarm_verified=bonus.swarm_verified:run_claim \
        --seeds 11,22,33,44,55 --out reports/bonus_benchmark_public.json
"""

from __future__ import annotations

import sqlite3
from typing import Any

from lab8.db import connect
from lab8.durability import InjectedCrash, issue_refund
from lab8.handoff import make_handoff
from lab8.mock_llm import complete, parse_delay_days
from lab8.runtime import run_readonly_investigators
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish, safe_dump
from lab8.shapes.workflow import SAFE_DENIAL_REASONS
from lab8.tools import compute_compensation, lookup_order, tool_cost
from lab8.trace import Trace

SHAPE = "swarm_verified"
# Facts the quote depends on (lab8.compensation). Fee and paid amounts are not
# touched by any agent, but checking them costs nothing once the row is read.
VERIFIED_FIELDS = ("delay_days", "status", "damage_verified", "shipping_fee_vnd", "paid_vnd")


def run_claim(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
    conn = connect(store_path)
    try:
        return _run(conn, claim_id, seed=seed, crash_at=crash_at)
    finally:
        conn.close()


def verify(
    conn: sqlite3.Connection,
    budget: Budget,
    *,
    order_id: str,
    principal_id: str,
    used: dict[str, Any],
) -> dict[str, Any]:
    """Compare the facts the swarm used with a fresh structured read.

    Returns {"ok": True} when they agree, else the corrected order, its quote and the
    names of the fields that disagreed. Values are not returned for the trace: field
    names are enough to audit the override and cannot carry user text.
    """
    budget.add_tool(tool_cost())
    fresh = lookup_order(conn, order_id, principal_id)
    if not fresh.get("visible"):
        return {"ok": False, "fields": [], "reason": fresh.get("reason"), "order": None, "quote": None}
    truth = fresh["order"]
    diff = [field for field in VERIFIED_FIELDS if used.get(field) != truth.get(field)]
    if not diff:
        return {"ok": True, "fields": []}
    budget.add_tool(tool_cost())
    return {"ok": False, "fields": diff, "reason": "fact_mismatch", "order": truth, "quote": compute_compensation(conn, truth)}


def _run(conn: sqlite3.Connection, claim_id: str, *, seed: int, crash_at: str | None) -> RunResult:
    budget = Budget()
    trace = Trace(make_run_id(SHAPE, claim_id, seed))

    def done(status: str, proposal: int = 0, reason: str | None = None) -> RunResult:
        return finish(
            conn,
            shape=SHAPE,
            claim_id=claim_id,
            seed=seed,
            status=status,
            proposal_amount=proposal,
            budget=budget,
            trace=trace,
            error_reason=reason,
        )

    # ---- reference swarm, unchanged -------------------------------------------------
    budget.add_tool(tool_cost())
    claim_row = conn.execute(
        "SELECT claim_id, principal_id, order_id, ticket FROM claims WHERE claim_id = ?",
        (claim_id,),
    ).fetchone()
    if claim_row is None:
        trace.add("error", {"reason": "unknown_claim"})
        return done("failed", reason="unknown_claim")

    ticket = claim_row["ticket"]
    complete(budget, seed=seed, purpose="peer", prompt=ticket)
    parsed_delay = parse_delay_days(ticket)
    complete(budget, seed=seed, purpose="parse", prompt=ticket)

    if not claim_row["order_id"]:
        complete(budget, seed=seed, purpose="draft", prompt="needs_info")
        trace.add("decision", {"status": "needs_info"})
        return done("needs_info", reason="missing_order_id")

    handoff = make_handoff(
        request_id=f"REQ-{claim_id}",
        claim_id=claim_id,
        task="check_applicable_policy",
        facts={},
        allowed_tools=["lookup_order", "lookup_policy", "compute_compensation"],
    )
    trace.add("handoff", safe_dump(handoff))
    investigated = run_readonly_investigators(conn, budget, handoff, principal_id=claim_row["principal_id"])
    order_view = investigated["tools"].get("lookup_order", {})
    trace.add(
        "investigator",
        {
            "lookup_order": order_view,
            "policy_count": len((investigated["tools"].get("lookup_policy") or {}).get("policies") or []),
        },
    )
    if not order_view.get("visible"):
        complete(budget, seed=seed, purpose="draft", prompt="escalated")
        return done("escalated", reason=order_view.get("reason"))

    order = dict(order_view["order"])
    # REFERENCE_WEAKNESS kept on purpose: one seed in five trusts the ticket delay.
    if parsed_delay is not None and parsed_delay != int(order["delay_days"]) and seed % 5 == 0:
        order["delay_days"] = parsed_delay
        trace.add("model_override", {"delay_days": parsed_delay})

    quote_payload = investigated["tools"]["compute_compensation"]
    if order["delay_days"] != order_view["order"]["delay_days"]:
        budget.add_tool(tool_cost())
        quote_payload = compute_compensation(conn, order)

    # ---- B3 addition: code verifier, one repair round ---------------------------------
    check = verify(
        conn,
        budget,
        order_id=claim_row["order_id"],
        principal_id=claim_row["principal_id"],
        used=order,
    )
    if not check["ok"]:
        if check["order"] is None:
            trace.add("verifier_override", {"fields": [], "action": "escalate", "reason": check["reason"]})
            complete(budget, seed=seed, purpose="draft", prompt="escalated")
            return done("escalated", reason=check["reason"])
        trace.add(
            "verifier_override",
            {
                "fields": check["fields"],
                "action": "requote_from_structured_order",
                "amount_before": int(quote_payload["amount_vnd"]),
                "amount_after": int(check["quote"]["amount_vnd"]),
            },
        )
        quote_payload = check["quote"]
    else:
        trace.add("verifier_ok", {"fields": list(VERIFIED_FIELDS)})

    # ---- reference swarm decision, on the verified quote ------------------------------
    proposal = int(quote_payload["amount_vnd"])
    trace.add("quote", quote_payload)
    complete(budget, seed=seed, purpose="draft", prompt=f"proposal={proposal}")

    if proposal <= 0:
        return done("denied", reason=quote_payload.get("reason"))

    try:
        outcome = issue_refund(conn, claim_id, proposal, crash_at=crash_at)
    except InjectedCrash:
        trace.add("crash", {"at": crash_at})
        trace.write()
        raise

    if outcome["conflict"]:
        return done("failed", proposal, "amount_conflict")
    if not outcome["ok"]:
        reason = outcome["reason"]
        return done("denied", proposal, reason if reason in SAFE_DENIAL_REASONS else "policy_denied")
    return done("resolved", proposal)
