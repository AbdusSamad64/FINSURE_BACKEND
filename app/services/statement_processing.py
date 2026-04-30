from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.categorization.llm_client import llm_categorize_batch
from app.categorization.rule_engine import apply_rules, load_rules
from app.models import Category
from app.services.extract_text import extract_pdf_with_ocr
from app.services.extract_transactions import (
    extract_transaction_of_alfalah,
    extract_transaction_of_easypaisa,
    extract_transaction_of_meezan,
    extract_transaction_of_ubl,
)


class UnsupportedBankError(ValueError):
    """Raised when a statement bank slug does not map to a configured parser."""


def parse_statement_date(date_str: str | None) -> datetime:
    if not date_str:
        return datetime.utcnow()

    for fmt in ("%b %d, %Y", "%d-%b-%Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return datetime.utcnow()


def normalize_extracted_transactions(raw_transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []

    for index, trx in enumerate(raw_transactions, start=1):
        incoming = trx.get("incoming") or trx.get("amount") or "-"
        outgoing = trx.get("outgoing") or "-"
        amount = 0.0
        trx_type = "debit"

        if incoming != "-" and float(str(incoming).replace(",", "")) > 0:
            amount = float(str(incoming).replace(",", ""))
            trx_type = "credit"
        elif outgoing != "-" and float(str(outgoing).replace(",", "")) > 0:
            amount = float(str(outgoing).replace(",", ""))
            trx_type = "debit"

        parsed_date = parse_statement_date(trx.get("date"))
        normalized.append(
            {
                "id": index,
                "trxNo": trx.get("transaction_id") or None,
                "date": parsed_date.date().isoformat(),
                "parsed_date": parsed_date,
                "description": trx.get("description") or "",
                "amount": amount,
                "trxType": trx_type,
                "category": "Uncategorized",
                "categorizedBy": None,
            }
        )

    return normalized


def extract_statement_transactions(
    file_path: str,
    bank_name: str,
    password: str | None = None,
) -> dict[str, Any]:
    _, total_no_pages = extract_pdf_with_ocr(file_path, password=password)
    bank_slug = (bank_name or "").strip().lower()
    complete_transactions: list[dict[str, Any]] = []
    account_number = None
    ubl_last_balance = None
    alfalah_last_balance = None

    if bank_slug == "easypaisa":
        for i in range(1, total_no_pages + 1):
            raw_file_path = f"output{i}.txt"
            transactions, acc_no = extract_transaction_of_easypaisa(
                filepath=raw_file_path,
                page_no=i,
                total_no_pages=total_no_pages,
                extract_account=(i == 1),
            )
            if acc_no:
                account_number = acc_no
            complete_transactions += transactions
    elif bank_slug == "meezan":
        for i in range(2, total_no_pages + 1):
            raw_file_path = f"output{i}.txt"
            transactions, acc_no = extract_transaction_of_meezan(
                filepath=raw_file_path,
                page_no=i,
                total_no_pages=total_no_pages,
                extract_account=(i == 2),
            )
            if acc_no:
                account_number = acc_no
            complete_transactions += transactions
    elif bank_slug == "ubl":
        for i in range(1, total_no_pages + 1):
            raw_file_path = f"output{i}.txt"
            transactions, acc_no, ubl_last_balance = extract_transaction_of_ubl(
                filepath=raw_file_path,
                page_no=i,
                total_no_pages=total_no_pages,
                extract_account=(i == 1),
                previous_balance=ubl_last_balance,
            )
            if acc_no:
                account_number = acc_no
            complete_transactions += transactions
    elif bank_slug == "alfalah":
        for i in range(1, total_no_pages + 1):
            raw_file_path = f"output{i}.txt"
            transactions, acc_no, alfalah_last_balance = extract_transaction_of_alfalah(
                filepath=raw_file_path,
                page_no=i,
                total_no_pages=total_no_pages,
                extract_account=(i == 1),
                previous_balance=alfalah_last_balance,
            )
            if acc_no:
                account_number = acc_no
            complete_transactions += transactions
    else:
        raise UnsupportedBankError("Unsupported bank statement.")

    return {
        "raw_transactions": complete_transactions,
        "transactions": normalize_extracted_transactions(complete_transactions),
        "account_number": account_number,
        "total_pages": total_no_pages,
    }


def categorize_transactions_in_memory(
    transactions: list[dict[str, Any]],
    db_session: Session,
) -> list[dict[str, Any]]:
    if not transactions:
        return transactions

    rules = load_rules(db_session)
    categories = db_session.query(Category).all()
    cat_name_to_id = {c.name: c.categID for c in categories}
    cat_id_to_name = {c.categID: c.name for c in categories}

    pending: list[dict[str, Any]] = []

    for trx in transactions:
        normalized_tx_type = "Incoming" if trx["trxType"] == "credit" else "Outgoing"
        categ_id = apply_rules(trx["description"], normalized_tx_type, rules)

        if categ_id:
            trx["category"] = cat_id_to_name.get(categ_id, "Uncategorized")
            trx["categorizedBy"] = "rule"
        else:
            pending.append(
                {
                    "trxID": trx["id"],
                    "description": trx["description"],
                    "tx_type": normalized_tx_type,
                    "amount": trx["amount"],
                }
            )

    if pending and cat_name_to_id:
        llm_results = llm_categorize_batch(
            pending,
            list(cat_name_to_id.keys()),
            cat_name_to_id,
        )
        result_map = {item["trxID"]: item for item in llm_results}
        for trx in transactions:
            match = result_map.get(trx["id"])
            if not match:
                continue
            trx["category"] = cat_id_to_name.get(match["categID"], "Uncategorized")
            trx["categorizedBy"] = match["categorized_by"]

    return transactions


def serialize_transactions_for_response(
    transactions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "id": trx["id"],
            "date": trx["date"],
            "description": trx["description"],
            "amount": trx["amount"],
            "trxType": trx["trxType"],
            "category": trx.get("category") or "Uncategorized",
            "categorizedBy": trx.get("categorizedBy"),
        }
        for trx in transactions
    ]
