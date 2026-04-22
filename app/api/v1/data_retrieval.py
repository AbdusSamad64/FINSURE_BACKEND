from fastapi import APIRouter,Depends
from fastapi.responses import JSONResponse
from app.utils.jwt_util import get_current_user
from .auth import connect_to_db

router = APIRouter(prefix="/api/v1/data", tags=["User-Data"])


# get uplaod history endpoint

@router.get('/my-upload-history')
def get_upload_history(
    curr_user: dict = Depends(get_current_user),
    conn = Depends(connect_to_db)
):
    with conn.cursor() as cursor:
        # Join through accounts → banks so we can show which bank each upload
        # belongs to. LEFT JOINs keep orphaned rows visible rather than silently
        # disappearing if an account row is ever missing.
        cursor.execute(
            """
            SELECT
                fu.filename,
                fu.file_type,
                fu.uploaded_at,
                fu.total_transactions,
                COALESCE(b.name, 'Unknown') AS bank
            FROM file_uploads fu
            LEFT JOIN accounts a ON a."accID" = fu."accID"
            LEFT JOIN banks b    ON b."bankID" = a."bankID"
            WHERE fu."userID" = %s
            ORDER BY fu.uploaded_at DESC;
            """,
            (curr_user["userID"],)
        )

        files = cursor.fetchall()  # fetch all matching rows

        # optionally, convert to list of dicts
        result = []
        for f in files:
            result.append({
                "fileName": f["filename"],
                "fileType": f["file_type"],
                "bank": f["bank"],
                "uploadDate": f["uploaded_at"],
                "transactionCount": f["total_transactions"],
                "status": "completed"
            })

        return {"history": result}



# get dashboard overview endpoint

@router.get('/my-dashboard-overview')
def get_dashboard_overview(
    curr_user: dict = Depends(get_current_user),
    conn = Depends(connect_to_db)
):
    with conn.cursor() as cursor:
        # fetch required columns for current user
        cursor.execute(
            """
            SELECT amount
            FROM transactions
            WHERE "userID" = %s AND "trxType" = 'credit';
            """,
            (curr_user["userID"],)
        )
        
        incoming = cursor.fetchall()  # fetch all matching rows

        cursor.execute(
            """
            SELECT amount
            FROM transactions
            WHERE "userID" = %s AND "trxType" = 'debit';
            """,
            (curr_user["userID"],)
        )
        
        outgoing = cursor.fetchall()  # fetch all matching rows

  
    totalIncome = sum([inc["amount"] for inc in incoming])
    totalExpenses = sum([out["amount"] for out in outgoing])
    netProfit = totalIncome - totalExpenses
        

    return {"dashboardSummary": {
        "totalIncome": totalIncome,
        "totalExpenses": totalExpenses,
        "netProfit": netProfit,
        "taxableIncome": 0  
    }}  

# get user raw transaction data

@router.get('/my-transaction-history')
def get_transactions_history(
    curr_user: dict = Depends(get_current_user),
    conn = Depends(connect_to_db)
):
    with conn.cursor() as cursor:
        # LEFT JOIN with categories so uncategorized rows still return a
        # row — those fall back to "Uncategorized" on the client.
        # trxType is kept separate from category so the UI can use it to
        # color amounts (credit = green, debit = red) while `category`
        # reflects the pipeline's output (Food, Rent, etc).
        cursor.execute(
            """
            SELECT
                t.date,
                t.amount,
                t."trxType",
                t."trxDetail",
                t."isTaxable",
                t.categorized_by,
                COALESCE(c.name, 'Uncategorized') AS category
            FROM transactions t
            LEFT JOIN categories c ON c."categID" = t."categID"
            WHERE t."userID" = %s
            ORDER BY t.date DESC;
            """,
            (curr_user["userID"],)
        )

        rows = cursor.fetchall()

        result = []
        for f in rows:
            result.append({
                "date": f["date"],
                "amount": f["amount"],
                "trxType": f["trxType"],          # credit / debit
                "category": f["category"],        # from categorization pipeline
                "description": f["trxDetail"],
                "taxable": bool(f["isTaxable"]) if f["isTaxable"] is not None else False,
                "categorizedBy": f["categorized_by"],  # 'rule' / 'llm-gemini' / 'llm-groq' / None
            })

        return {"transactions": result}