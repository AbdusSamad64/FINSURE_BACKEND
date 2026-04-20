import re
from sqlalchemy.orm import Session
from app.models import Category, TransactionRule

def _clean(text: str) -> str:
    """Uppercase and strip extra whitespace."""
    return re.sub(r"\s+", " ", str(text).strip().upper())

def load_rules(db: Session):
    """Fetch rules from DB, joined with categories.
    Returns a list of dictionaries containing rule details and category names.
    """
    rules = db.query(TransactionRule).all()
    # Pre-loading rules with category names for logging/convenience if needed
    # but the primary return is the rule objects for matching
    return rules

def apply_rules(description: str, tx_type: str, rules: list[TransactionRule]) -> int | None:
    """
    Walk rules in order; return categID on first match, else None.
    """
    desc = _clean(description)
    ttype = _clean(tx_type) if tx_type else ""

    for rule in rules:
        # Check tx_type gate
        # rule.tx_type: 'Incoming', 'Outgoing', or NULL
        if rule.tx_type and rule.tx_type.upper() not in ttype:
            continue

        # Check exclusion patterns
        excluded = False
        if rule.exclude:
            for p in rule.exclude:
                if re.search(p, desc, re.IGNORECASE):
                    excluded = True
                    break
        if excluded:
            continue

        # Check keyword patterns (OR logic)
        for p in rule.keywords:
            if re.search(p, desc, re.IGNORECASE):
                return rule.categID

    return None  # no rule matched
