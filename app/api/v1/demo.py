from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.database import SessionLocal
from app.services.statement_processing import (
    UnsupportedBankError,
    categorize_transactions_in_memory,
    extract_statement_transactions,
    serialize_transactions_for_response,
)
from app.utils.file_helpers import delete_temp_file, detect_file_type, save_temp_file
from app.utils.report_logic import build_category_breakdown_report_from_transactions

router = APIRouter(prefix="/api/v1/demo", tags=["Public Demo"])


@router.post("/statement")
async def process_demo_statement(
    files: list[UploadFile] = File(..., alias="file"),
    password: str | None = Form(None),
    file_type: str = Form(...),
    bank_name: str = Form(...),
):
    if len(files) != 1:
        raise HTTPException(status_code=400, detail="Please upload exactly one statement.")

    file = files[0]
    temp_path = None
    total_no_pages = 0

    try:
        detected_type = detect_file_type(file.content_type)
        if detected_type.get("type") != "pdf":
            raise HTTPException(
                status_code=400,
                detail="The public demo currently supports PDF bank statements only.",
            )

        if file_type not in {"bank_statement", "mobile_wallet_statement"}:
            raise HTTPException(status_code=400, detail="Unsupported statement type.")

        temp_path = save_temp_file(file)

        try:
            extracted = extract_statement_transactions(
                str(temp_path),
                bank_name=bank_name,
                password=password,
            )
        except ValueError as exc:
            return JSONResponse(
                status_code=401,
                content={"status": "PASSWORD_REQUIRED", "message": str(exc)},
            )
        except UnsupportedBankError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        total_no_pages = extracted["total_pages"]

        db_session = SessionLocal()
        try:
            categorized = categorize_transactions_in_memory(
                extracted["transactions"],
                db_session,
            )
        finally:
            db_session.close()

        serialized_transactions = serialize_transactions_for_response(categorized)
        report = build_category_breakdown_report_from_transactions(
            categorized,
            report_id="demo-category-breakdown",
            title="Demo Category Breakdown",
            generated_date=datetime.utcnow().isoformat(),
        )

        return {
            "bank": bank_name,
            "filename": file.filename,
            "accountNumber": extracted["account_number"],
            "totalTransactions": len(serialized_transactions),
            "totalPages": total_no_pages,
            "transactions": serialized_transactions,
            "report": report,
        }
    finally:
        if temp_path:
            delete_temp_file(temp_path)
        for i in range(1, total_no_pages + 1):
            delete_temp_file(f"output{i}.txt")
        await file.close()
