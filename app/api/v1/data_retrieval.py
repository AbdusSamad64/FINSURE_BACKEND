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
        # fetch required columns for current user
        cursor.execute(
            """
            SELECT filename, file_type, uploaded_at, total_transactions
            FROM file_uploads
            WHERE "userID" = %s
            ORDER BY uploaded_at DESC;
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
        # fetch required columns for current user
        cursor.execute(
            """
            SELECT date, amount, "trxType", "trxDetail"
            FROM transactions
            WHERE "userID" = %s
            ORDER BY date DESC;
            """,
            (curr_user["userID"],)
        )
        
        files = cursor.fetchall()  # fetch all matching rows

        # optionally, convert to list of dicts
        result = []
        for f in files:
            result.append({
                "date": f["date"],
                "amount": f["amount"],
                "category": f["trxType"],
                "description": f["trxDetail"],
                "taxable": 'false',
            })

        return {"transactions": result}    