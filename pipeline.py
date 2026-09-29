from agents import (transaction_agent, spend_agent, usage_agent, support_agent,
                    profile_agent, transfer_agent, life_event_agent)

SWARM = [transaction_agent, spend_agent, usage_agent,
         support_agent, profile_agent, transfer_agent]


def analyse_day(day, customer_id, store, board, memory, tracer=None):
    """Swarm agents publish findings, then the life-event agent updates memory and infers."""
    for agent in SWARM:
        findings = agent.run(customer_id, store, day)
        board.publish(customer_id, agent.AGENT_NAME, findings)
        if tracer:
            summary = [{"signal": f.signal, "confidence": f.confidence, "evidence": f.evidence}
                       for f in findings]
            tracer.log(day, agent.AGENT_NAME, customer_id, len(findings), summary)

    life_event_agent.update_memory(customer_id, board.findings_for(customer_id), memory, day)
    return life_event_agent.infer(customer_id, memory, day)