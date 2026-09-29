# state -> {signal pattern: weight}. "*" matches anything after the colon.
RULES = {
    "medical_hardship": {
        "spend_spike:healthcare": 1.0, "spend_spike:pharmacy": 0.5,
        "search_theme:medical": 0.8, "support_theme:medical": 1.0,
        "income_drop": 0.7, "income_stopped": 0.5,
    },
    "job_loss_or_income_disruption": {
        "income_drop": 1.0, "income_stopped": 1.0,
        "support_theme:job_loss": 1.0, "search_theme:job_loss": 0.8, "login_drop": 0.2,
    },
    "financial_distress_general": {
        "income_drop": 0.5, "support_theme:financial_stress": 0.8,
        "search_theme:financial_stress": 0.8, "spend_drop:*": 0.2,
    },
    "new_child_life_event": {
        "profile_change:dependents_change": 1.5, "recurring_started:new_baby": 1.5,
        "spend_spike:baby_products": 1.2, "support_theme:new_baby": 1.0,
        "search_theme:new_baby": 0.8, "income_drop": 0.6,
        "spend_spike:healthcare": 0.4, "spend_spike:pharmacy": 0.4,
    },
    "marriage_or_relationship_change": {
        "profile_change:marital_status_change": 1.5, "support_theme:marriage": 1.0,
        "search_theme:marriage": 0.8,
    },
    "relocation": {
        "profile_change:address_change": 1.2, "support_theme:relocation": 1.0,
        "search_theme:relocation": 0.8,
    },
    "churn_risk": {
        "external_self_transfer": 1.5, "income_swept_out": 1.5,
        "recurring_stopped:*": 0.7, "feature_theme:churn": 1.0,
        "support_theme:churn": 1.2, "search_theme:churn": 0.8,
        "support_theme:dissatisfaction": 0.8, "support_denied": 0.6,
        "login_drop": 0.8, "card_activity_drop": 0.8,
    },
    "potential_fraud_or_takeover": {
        "support_theme:fraud": 1.5, "search_theme:fraud": 0.8,
    },
    "retirement_transition": {
        "support_theme:retirement": 1.0, "search_theme:retirement": 0.8,
    },
}

# How much we trust a finding, depending on the agent's own confidence in it.
CONFIDENCE_FACTOR = {"low": 0.3, "medium": 0.6, "high": 1.0}
# Nonspecific signals: they fit many stories, so they never convince on their own.
SOFT_SIGNALS = [
    "login_drop", "login_spike", "card_activity_drop", "spend_drop:*",
    "support_denied", "support_theme:dissatisfaction",
]