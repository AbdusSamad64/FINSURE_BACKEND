import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.database import SessionLocal
from app.categorization.rule_engine import load_rules, apply_rules

def test_rule_matching():
    db = SessionLocal()
    try:
        rules = load_rules(db)
        print(f"Loaded {len(rules)} rules from DB.")
        
        test_cases = [
            ("ATM CASH WITHDRAWAL", "Outgoing", "Withdrawal"),
            ("PAYONEER PAYMENT", "Incoming", "Freelance Income"),
            ("NETFLIX SUBSCRIPTION", "Outgoing", "Subscriptions"),
            ("ELECTRICITY BILL", "Outgoing", "Utilities and Bills"),
            ("UNKNOWN TRX", "Outgoing", None),
        ]
        
        # Get category names for verification
        from app.models import Category
        cats = db.query(Category).all()
        id_to_name = {c.categID: c.name for c in cats}
        
        for desc, ttype, expected in test_cases:
            res_id = apply_rules(desc, ttype, rules)
            res_name = id_to_name.get(res_id) if res_id else None
            status = "PASS" if res_name == expected else "FAIL"
            print(f"[{status}] Desc: {desc:25} | Result: {res_name} | Expected: {expected}")
            
    finally:
        db.close()

if __name__ == "__main__":
    test_rule_matching()
