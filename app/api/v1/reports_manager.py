from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from .auth import connect_to_db
from app.utils.jwt_util import get_current_user
from app.models.reports_models import ReportRequest

router = APIRouter(prefix="/api/v1/reports", tags=["Reports"])

@router.post("/generate")
def generate_report(
    payload: ReportRequest,
    curr_user: dict = Depends(get_current_user),
    conn = Depends(connect_to_db)
):
    # report title mapping 
    if payload.reportType == "income_expense":
        title = "Income vs Expense Report"
    elif payload.reportType == "tax_summary":
        title = "Tax Summary"
    elif payload.reportType == "cashflow":
        title = "Cashflow"
    else:
        raise HTTPException(status_code=400, detail="Unsupported report type")

    try:
        with conn.cursor() as cursor:

            # get first & last transaction dates 
            cursor.execute(
                """
                SELECT 
                    MIN("date") AS first_trx,
                    MAX("date") AS last_trx
                FROM transactions
                WHERE "userID" = %s;
                """,
                (curr_user["userID"],)
            )

            result = cursor.fetchone()
            print('result:', result)

            if not result["first_trx"] or not result["last_trx"]:
                raise HTTPException(
                    status_code=400,
                    detail="No transactions found for this user"
                )

            first_trx_date = result["first_trx"].date()
            last_trx_date = result["last_trx"].date()

            # date validation 
            if payload.startDate < first_trx_date:
                raise HTTPException(
                    status_code=400,
                    detail=f"Start date cannot be earlier than first transaction date ({first_trx_date})"
                )

            if payload.endDate > last_trx_date:
                raise HTTPException(
                    status_code=400,
                    detail=f"End date cannot be later than last transaction date ({last_trx_date})"
                )

            # insert report 
            generated_on = datetime.utcnow().date()

            cursor.execute(
                """
                INSERT INTO reports (title, report_type, generated_on, "from", "to", "userID")
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING report_id;
                """,
                (
                    title,
                    payload.reportType,
                    generated_on,
                    payload.startDate,
                    payload.endDate,
                    curr_user["userID"]
                )
            )

            report_id = cursor.fetchone()["report_id"]
            conn.commit()

        return {
            "success": True,
            "report": {
                "id": str(report_id),
                "title": title,
                "generatedDate": datetime.utcnow().isoformat() + "Z",
                "type": payload.reportType,
                "dateRange": f"{payload.startDate} to {payload.endDate}"
            }
        }

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
