import os
import sys

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.database import SessionLocal
from app.models import Category, TransactionRule

RULES = [
    # ── WITHDRAWAL ──────────────────────────────────────────────────────────
    {
        "keywords": [r"\bATM\b", r"CASH WITHDRAWAL", r"CASH WDR", r"CDM WITHDRAWAL",
                     r"WITHDRAW", r"CASH ADVANCE",
                     r"ATM CASH WITHDRAWAL",          # Meezan
                     r"CASH WITHDRAWAL - ATM",        # UBL
                     r"CASH WITHDRAWAL - 1.?LINK",    # UBL 1-Link
                     r"1.?LINK WITHDRAWAL(?! FEE)",   # UBL (exclude fee)
                     r"Cash Withdrawal from 1-Link",  # Alfalah
                     r"Cash withdrawal from ATM",     # Alfalah
                     r"CASH WITHDRAWAL$",             # bare trailing
                     r"\bCASH WITHDRAWAL\b"],
        "tx_type":  "Outgoing",
        "category": "Withdrawal",
    },

    # ── BANK SERVICE CHARGES ─────────────────────────────────────────────────
    {
        "keywords": [r"SERVICE CHARGE", r"BANK CHARGE", r"ANNUAL FEE", r"CARD FEE",
                     r"MAINTENANCE FEE", r"SMS ALERT", r"WITHHOLDING TAX", r"\bWHT\b",
                     r"EXCISE DUTY", r"STAMP DUTY", r"LATE PAYMENT", r"PENALTY",
                     r"INTEREST CHARGED", r"OVERDUE", r"DEBIT CARD FEE",
                     r"CHEQUE BOOK", r"ACCOUNT MAINTENANCE", r"INTER-?BANK FEE",
                     r"TRANSACTION FEE", r"PROCESSING FEE", r"LOCKER CHARGES",
                     r"FED ON", r"FEDERAL EXCISE",
                     r"TKFL\s*DEDU?CTION", r"TKFL COVERAGE",  # Meezan TKFL
                     r"1LINK WITHDRAWAL FEE",                  # UBL interbank fee
                     r"W\.?H\.?TAX ON PROFIT",                 # Alfalah WHT on profit
                     r"WITHHOLDING TAX DEBIT"],                # Meezan WHT
        "tx_type":  None,
        "category": "Bank Service Charges",
    },

    # ── FREELANCE INCOME ─────────────────────────────────────────────────────
    {
        "keywords": [r"PAYONEER", r"UPWORK", r"FIVERR", r"FREELANCER\.COM",
                     r"TOPTAL", r"GURU\.COM", r"PEOPLE\s?PER\s?HOUR",
                     r"99DESIGNS", r"HUBSTAFF", r"REMIT(?:TANCE)?",
                     r"INWARD REMITTANCE", r"INWARD TT",
                     r"FOREIGN CREDIT", r"FOREIGN INWARD", r"FCY CREDIT",
                     r"USD.*CREDIT", r"EUR.*CREDIT", r"GBP.*CREDIT",
                     r"CAD.*CREDIT", r"AUD.*CREDIT",
                     r"STRIPE", r"WISE(?:\s+PAYMENT)?", r"PAYPAL.*CREDIT",
                     r"TRANSFERWISE", r"REVOLUT.*CREDIT",
                     r"FREELANCE", r"CONSULTANCY FEE", r"PROJECT PAYMENT",
                     r"CLIENT PAYMENT", r"WORK ORDER",
                     r"SWIFT.*CREDIT", r"INTERNATIONAL.*CREDIT"],
        "tx_type":  "Incoming",
        "category": "Freelance Income",
        "exclude":  [r"REFUND", r"REVERSAL", r"RETURN"],
    },

    # ── SALARY ───────────────────────────────────────────────────────────────
    {
        "keywords": [r"\bSALARY\b", r"\bPAYROLL\b", r"\bMONTHLY PAY\b",
                     r"SALARY CREDIT", r"PAY CREDIT", r"WAGES",
                     r"STIPEND", r"MONTHLY ALLOWANCE", r"EMOLUMENT",
                     r"TRANSFER CMS SAL",   # Meezan CMS salary (e.g. SAL-JUL24)
                     r"CMS SAL-"],
        "tx_type":  "Incoming",
        "category": "Salary",
        "exclude":  [r"ADVANCE", r"DEDUCTION"],
    },

    # ── REFUND ───────────────────────────────────────────────────────────────
    {
        "keywords": [r"\bREFUND\b", r"REVERSAL", r"CHARGEBACK",
                     r"CASHBACK", r"CASH BACK", r"CREDIT REVERSAL",
                     r"RETURNED PAYMENT", r"MONEY BACK", r"REBATE",
                     r"REIMBURSEMENT", r"OVERPAYMENT CREDIT",
                     r"TRANSACTION REVERSED", r"FAILED.*CREDIT",
                     r"ERRONEOUS.*CREDIT", r"ERROR.*CREDIT",
                     r"PAYMENT OF PROFIT",      # Meezan profit payment
                     r"PROFIT PAID",            # Alfalah profit
                     r"QTRLYDISTR",             # Meezan quarterly distribution
                     r"CMS QTRLY"],
        "tx_type":  "Incoming",
        "category": "Refund",
    },

    # ── SUBSCRIPTIONS ────────────────────────────────────────────────────────
    {
        "keywords": [r"NETFLIX", r"SPOTIFY", r"YOUTUBE.*PREMIUM",
                     r"AMAZON PRIME", r"APPLE.*SUBSCRI", r"GOOGLE.*PLAY",
                     r"MICROSOFT.*365", r"OFFICE\s?365", r"ADOBE.*SUBSCRI",
                     r"DROPBOX", r"CANVA", r"FIGMA", r"GITHUB.*SUBSCRI",
                     r"CHATGPT", r"OPENAI", r"MIDJOURNEY", r"CLAUDE",
                     r"ZOOM.*PRO", r"SLACK.*SUBSCRI", r"NOTION.*SUBSCRI",
                     r"GRAMMARLY", r"JASPER", r"SEMRUSH", r"AHREFS",
                     r"HOSTINGER", r"GODADDY", r"NAMECHEAP",
                     r"DIGITAL\s*OCEAN", r"LINODE", r"VULTR", r"AWS.*CHARGE",
                     r"HEROKU", r"VERCEL", r"SUBSCRI(?:PTION)?",
                     r"MEMBERSHIP FEE", r"RENEWAL FEE", r"ANNUAL RENEWAL"],
        "tx_type":  "Outgoing",
        "category": "Subscriptions",
    },

    # ── UTILITIES & BILLS ────────────────────────────────────────────────────
    {
        "keywords": [r"ELECTRICITY", r"WAPDA", r"LESCO", r"HESCO", r"IESCO",
                     r"MEPCO", r"PESCO", r"QESCO", r"FESCO", r"GEPCO",
                     r"GAS BILL", r"SSGC", r"SNGPL",
                     r"WATER BILL", r"KWSB", r"LWASA",
                     r"INTERNET BILL", r"BROADBAND", r"PTCL", r"NAYATEL",
                     r"STORMFIBER", r"CYBERNET", r"TRANSWORLD",
                     r"MOBILE BILL", r"TELECOM BILL", r"UTILITY BILL",
                     r"CABLE TV", r"DISH TV", r"DTH",
                     r"INSURANCE PREMIUM", r"EFU", r"JUBILEE LIFE",
                     r"STATE LIFE", r"ADAMJEE", r"PAKISTAN LIFE",
                     r"KUICKPAY",                       # KuickPay bill portal
                     r"UTILITY BILL PAYMENT",           # Alfalah
                     r"UBL DIGITAL.*BILL PAYMENT",      # UBL Zong/utility
                     r"BILL PAYMENT TO ZONG",           # UBL Zong specific
                     r"CMPAK",                          # Zong parent (Easypaisa)
                     r"Payment-CMPAK"],
        "tx_type":  "Outgoing",
        "category": "Utilities and Bills",
    },

    # ── PERSONAL TRANSFER ────────────────────────────────────────────────────
    {
        "keywords": [r"\bIBFT\b", r"INTER.?BANK.*TRANSFER",
                     r"ONLINE TRANSFER", r"FUND TRANSFER", r"OWN TRANSFER",
                     r"\bRAAST\b", r"RAAST PYMT", r"RAAST P2P",
                     r"FUNDSTRANSFER RAAST",             # Alfalah no-space variant
                     r"EASYPAISA", r"JAZZCASH", r"JAZZ CASH",
                     r"MB IBFT TO JAZZCASH",             # Meezan→JazzCash
                     r"MOBILINK MICROFINANCE",           # JazzCash bank name
                     r"TELENOR MICROFINANCE",            # Easypaisa bank name
                     r"NIFT", r"RTGS",
                     r"MBANKING FUNDS TRANSFER",         # Meezan mobile
                     r"INTERNET FUNDS TRANSFER",         # Meezan internet
                     r"FUNDS TRANSFER STAN",             # Meezan STAN pattern
                     r"INTERNAL FUNDS TRANSFER",         # UBL internal
                     r"DIGITAL APP-IBFT",                # UBL IBFT
                     r"UBL DIGITAL.*FUNDS TRANSFER",
                     r"Bank Transfer",                   # Easypaisa
                     r"Raast Payment",                   # Easypaisa Raast
                     r"Money Transfer",                  # Easypaisa
                     r"TRF TO", r"TRF FROM",
                     r"SENT TO", r"RECEIVED FROM",
                     r"CHEQUE.*DEPOSITED",               # cheque deposits
                     r"CHEQUE",               # cheque deposits
                     r"ACH CREDIT", r"ACH DEBIT",
                     r"IPS TRANSFER"],
        "tx_type":  None,
        "category": "Personal Transfer",
        "exclude":  [r"SALARY", r"PAYROLL", r"CMS SAL",
                     r"UTILITY", r"BILL PAYMENT", r"KUICKPAY",
                     r"CMPAK", r"ZONG"],
    },
]

def seed_rules():
    db = SessionLocal()
    try:
        print("Fetching categories...")
        categories = db.query(Category).all()
        cat_map = {c.name.strip().lower(): c.categID for c in categories}
        
        # Ensure all required categories exist
        required_categories = set(rule["category"] for rule in RULES)
        for cat_name in required_categories:
            if cat_name.strip().lower() not in cat_map:
                print(f"Adding missing category: {cat_name}")
                new_cat = Category(name=cat_name)
                db.add(new_cat)
                db.flush() # Populate categID
                cat_map[cat_name.strip().lower()] = new_cat.categID
        
        print(f"Current Categories in map: {cat_map}")

        # Clear existing rules to avoid duplicates on re-run
        print("Clearing existing rules...")
        db.query(TransactionRule).delete()
        
        # Insert rules
        for rule_data in RULES:
            categ_id = cat_map.get(rule_data["category"].strip().lower())
            if not categ_id:
                print(f"Warning: Category {rule_data['category']} not found even after adding.")
                continue
                
            rule = TransactionRule(
                categID=categ_id,
                keywords=rule_data["keywords"],
                tx_type=rule_data["tx_type"],
                exclude=rule_data.get("exclude")
            )
            db.add(rule)
            print(f"Added rule for category: {rule_data['category']}")
        
        db.commit()
        print("Successfully seeded transaction rules! ✅")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding rules: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_rules()
