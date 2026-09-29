AGENT_NAME = "action_agent"

# state -> (action, subtype, needs_human). Used only when confidence is HIGH.
# The subtypes are free text, so change them however you like.
PLAYBOOK = {
    "medical_hardship": ("support_intervention", "medical_hardship_payment_plan", True),
    "job_loss_or_income_disruption": ("support_intervention", "income_disruption_payment_flexibility", True),
    "financial_distress_general": ("support_intervention", "financial_hardship_outreach", False),
    "new_child_life_event": ("personalized_offer", "childcare_savings_or_insurance_offer", True),
    "marriage_or_relationship_change": ("personalized_offer", "joint_account_or_planning_offer", True),
    "relocation": ("personalized_offer", "relocation_services_offer", True),
    "churn_risk": ("proactive_retention_outreach", "retention_gesture", False),
    "potential_fraud_or_takeover": ("compliance_fraud_hold", "suspected_takeover_review", True),
    "retirement_transition": ("relationship_manager_escalation", "retirement_planning_conversation", True),
}


def _checkpoint(as_of, state, band, action, subtype, hitl, notes):
    return {
        "as_of_time": as_of.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inferred_state": state,
        "confidence_band": band,
        "action": action,
        "action_subtype": subtype,
        "hitl_status": hitl,
        "notes": notes,
    }


def explain(inf):
    """Built from the evidence that produced the decision, not written after the fact."""
    if inf["state"] == "no_significant_event":
        return "No signals above threshold."
    top = sorted(inf["evidence"], key=lambda x: x[1], reverse=True)[:4]
    signals = ", ".join(f"{s} ({w})" for s, w, _ in top)
    return (f"{inf['state']} scored {inf['score']:.1f} from {len(inf['agents'])} agent(s) "
            f"[{', '.join(sorted(inf['agents']))}]. Key evidence: {signals}.")


def decide(inf, guardrail_hits, as_of):
    state, band, why = inf["state"], inf["band"], explain(inf)

    # 1) Guardrails override everything.
    if guardrail_hits:
        h = guardrail_hits[0]
        return _checkpoint(as_of, h["state"] or state, "high", h["action"], h["subtype"], "escalated",
                           f"GUARDRAIL '{h['rule']}' matched event {h['event_id']}; "
                           f"autonomous outreach halted. {why}")

    # 2) Too weak to act on.
    if state == "no_significant_event" or band == "low":
        return _checkpoint(as_of, state, band, "no_action", None, "auto_approved",
                           f"Below action threshold. {why}")

    # 3) Two states are too close to call: send to a human instead of guessing.
    if inf["ambiguous"]:
        return _checkpoint(as_of, state, band, "relationship_manager_escalation",
                           "ambiguous_signals_review", "escalated",
                           f"Ambiguous: runner-up {inf['runner_up']}. {why}")

    # 4) Medium: keep watching.
    if band == "medium":
        return _checkpoint(as_of, state, band, "no_action", None, "auto_approved",
                           f"Watching, not enough corroboration to act yet. {why}")

    # 5) High confidence: follow the playbook.
    action, subtype, needs_human = PLAYBOOK.get(
        state, ("relationship_manager_escalation", "manual_review", True))
    return _checkpoint(as_of, state, band, action, subtype,
                       "escalated" if needs_human else "auto_approved", why)