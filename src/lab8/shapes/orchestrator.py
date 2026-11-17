"""Shape C: read-only investigation, code-based quotes and host-controlled refunds.

Handoffs contain only allowed fields and tools. Reasons are restricted to fixed
codes before they reach trace events or RunResult.
"""

from __future__ import annotations

import sqlite3

from lab8.db import connect
from lab8.durability import issue_refund
from lab8.handoff import make_handoff
from lab8.mock_llm import complete
from lab8.runtime import run_readonly_investigators
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish
from lab8.tools import compute_compensation, get_claim_view, tool_cost
from lab8.trace import Trace


SAFE_REASONS = frozenset({
    "unknown_claim", "missing_order_id", "missing_order", "not_found",
    "outside_principal_scope", "no_entitlement", "order_status_cancelled",
    "order_status_in_transit", "approval_claim_mismatch", "approval_expired",
    "approval_revoked", "missing_approval", "non_positive_amount",
    "order_already_refunded", "order_total_changed", "capped_to_zero",
    "amount_conflict", "committed", "idempotent_replay", "policy_denied",
})


def _safe_reason(reason: str | None, *, fallback: str = "policy_denied") -> str | None:
    # Host and quote reasons can embed untrusted database values.
    return reason if reason is None or reason in SAFE_REASONS else fallback


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


def _run(
    conn: sqlite3.Connection,
    claim_id: str,
    *,
    seed: int,
    crash_at: str | None,
) -> RunResult:
    budget = Budget()
    trace = Trace(make_run_id("orchestrator", claim_id, seed))

    def respond(status: str, proposal: int = 0, reason: str | None = None) -> RunResult:
        reason = _safe_reason(reason)
        # Neither the model nor the trace receives ticket text or raw database rows.
        complete(budget, seed=seed, purpose="draft", prompt=f"status={status};proposal={proposal}")
        trace.add("decision", {"status": status, "proposal_amount": proposal, "reason": reason})
        return finish(
            conn,
            shape="orchestrator",
            claim_id=claim_id,
            seed=seed,
            status=status,
            proposal_amount=proposal,
            budget=budget,
            trace=trace,
            error_reason=reason,
        )

    budget.add_tool(tool_cost())
    claim = get_claim_view(conn, claim_id)
    trace.add("claim", {"found": claim["found"], "has_order_id": bool(claim.get("order_id"))})
    if not claim["found"]:
        return respond("failed", reason="unknown_claim")
    if not claim.get("order_id"):
        return respond("needs_info", reason="missing_order_id")

    # MockLLM accounts for planning; capabilities and all money decisions stay in code.
    complete(budget, seed=seed, purpose="plan", prompt="check_owner_order_current_policy_refund_history")
    handoff = make_handoff(
        request_id=f"REQ-{claim_id}",
        claim_id=claim_id,
        task="check_applicable_policy",
        facts={},
        allowed_tools=["lookup_order", "lookup_policy", "lookup_refund_history"],
    )
    trace.add("handoff", handoff)
    investigated = run_readonly_investigators(
        conn, budget, handoff, principal_id=claim["principal_id"]
    )
    tools = investigated["tools"]
    order_view = tools["lookup_order"]
    # Log only operational facts, never order_id, carrier or other free-form values.
    trace.add(
        "investigator",
        {
            "visible": bool(order_view["visible"]),
            "policy_count": len(tools["lookup_policy"]["policies"]),
            "refunded_vnd": tools["lookup_refund_history"].get("refunded_vnd", 0),
        },
    )
    if not order_view["visible"]:
        return respond("escalated", reason=order_view["reason"])

    budget.add_tool(tool_cost())
    quote = compute_compensation(conn, order_view["order"])
    proposal = int(quote["amount_vnd"])
    trace.add("quote", {"amount_vnd": proposal})
    if proposal <= 0:
        return respond("denied", reason=_safe_reason(quote["reason"], fallback="no_entitlement"))

    # Flush before the write so an injected crash still leaves a safe trace.
    trace.add("refund_request", {"proposal_amount": proposal})
    trace.write()
    outcome = issue_refund(conn, claim_id, proposal, crash_at=crash_at)
    reason = _safe_reason(outcome["reason"])
    trace.add("refund_outcome", {"ok": outcome["ok"], "reason": reason})
    if not outcome["ok"]:
        status = "failed" if outcome["conflict"] else "denied"
        return respond(status, proposal, reason)
    return respond("resolved", proposal)
