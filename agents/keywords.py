THEMES = {
    "medical": ["hospital", "surgery", "medical", "doctor", "emergency room", "treatment", "clinic", "prescription"],
    "financial_stress": ["hardship", "payment plan", "payment arrangement", "can't pay", "cannot pay",
                         "behind on", "late fee", "deferment", "income dropped", "struggling"],
    "job_loss": ["laid off", "lost my job", "unemployment", "redundan", "terminated", "severance"],
    "new_baby": ["baby", "newborn", "pregnan", "maternity", "paternity", "daycare", "childcare",
                 "nursery", "child education", "education savings", "college fund"],
    "marriage": ["wedding", "engaged", "fiance", "spouse", "joint account", "name change"],
    "relocation": ["relocat", "moving to", "moved to", "new address", "new city", "movers"],
    "home_buying": ["mortgage", "home loan", "down payment", "realtor", "house hunting"],
    "retirement": ["retire", "pension", "401k", "social security"],
    "fraud": ["unauthorized", "fraud", "scam", "stolen", "hacked", "didn't make", "locked out"],
    "churn": ["cancel", "close my account", "close account", "switch bank", "competitor"],
    "dissatisfaction": ["dispute", "transaction fee", "fee waiv", "wasn't disclosed", "not disclosed",
                        "refund this", "unfair", "overcharg", "complaint"],
    "urgent": ["urgent", "immediately", "asap", "unacceptable", "furious", "terrible", "ridiculous"],
}


def match_themes(text):
    """Return {theme: [matched words]} for a piece of text."""
    text = (text or "").lower().replace("\u2019", "'")
    hits = {}
    for theme, words in THEMES.items():
        found = [w for w in words if w in text]
        if found:
            hits[theme] = found
    return hits