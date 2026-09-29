def review(checkpoint, explanation, auto_mode=False):
    """
    If the proposed hitl_status is 'escalated', actually stop and ask a human.
    Returns the checkpoint with hitl_status upgraded to human_approved /
    human_rejected / human_modified, and logs what was shown.
    """
    if checkpoint["hitl_status"] != "escalated":
        return checkpoint, None   # low-stakes or auto-approved, no human needed

    print("\n" + "=" * 70)
    print(f"HUMAN REVIEW NEEDED  |  as of {checkpoint['as_of_time']}")
    print(f"  inferred_state : {checkpoint['inferred_state']}")
    print(f"  confidence     : {checkpoint['confidence_band']}")
    print(f"  proposed action: {checkpoint['action']} ({checkpoint['action_subtype']})")
    print(f"  reasoning      : {explanation}")
    print("=" * 70)

    if auto_mode:
        # Non-interactive runs (e.g. batch scoring) auto-approve so the pipeline doesn't block.
        decision = "a"
    else:
        decision = input("Approve (a) / Reject (r) / Modify (m) / Why? (w): ").strip().lower()
        while decision == "w":
            print(f"  Because: {explanation}")
            decision = input("Approve (a) / Reject (r) / Modify (m): ").strip().lower()

    record = {"as_of_time": checkpoint["as_of_time"], "shown": dict(checkpoint),
              "explanation": explanation, "decision": decision}

    if decision == "r":
        checkpoint["action"], checkpoint["action_subtype"] = "no_action", None
        checkpoint["hitl_status"] = "human_rejected"
    elif decision == "m":
        new_action = input(f"  New action (blank keeps '{checkpoint['action']}'): ").strip()
        if new_action:
            checkpoint["action"] = new_action
        checkpoint["hitl_status"] = "human_modified"
    else:
        checkpoint["hitl_status"] = "human_approved"

    record["final"] = dict(checkpoint)
    return checkpoint, record