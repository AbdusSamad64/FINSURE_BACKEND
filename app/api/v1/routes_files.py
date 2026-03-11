from fastapi import APIRouter, UploadFile, File,Form, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from app.utils.file_helpers import detect_file_type,save_temp_file,delete_temp_file
from app.services.extract_text import extract_pdf_with_ocr
from app.services.extract_transactions import extract_transaction_of_easypaisa,extract_transaction_of_meezan,extract_transaction_of_ubl,extract_transaction_of_alfalah
from app.utils.jwt_util import get_current_user
from app.models.accounts_models import NewAccount
from .auth import connect_to_db
from hashlib import sha256
from datetime import datetime
import uuid


router=APIRouter()


def calculate_trx_hash(trx: dict) -> str:
    """
    Generate a SHA256 hash for a transaction dict
    """
    key = f"{trx.get('date')}_{trx.get('description')}_{trx.get('amount')}"
    return sha256(key.encode('utf-8')).hexdigest()

def save_transactions_to_db(transactions, account, user_id, file_info, conn):
    """
    Save transactions to DB with duplicate check using trxHash
    All inserts happen in a single DB transaction; rollback on error
    """
    total_inserted = 0
    try:
        with conn.cursor() as cursor:
            # start transaction
            cursor.execute("BEGIN;")
            
            # get account info
            cursor.execute('SELECT * FROM accounts WHERE "accountNo"=%s AND "userID"=%s;', (account, user_id))
            account_row = cursor.fetchone()
            if not account_row:
                raise ValueError("Account not found or not associated with user")
            accID = account_row["accID"]

            for trx in transactions:
                # Determine amount and type
                incoming = trx.get("incoming") or trx.get("amount") or "-"
                outgoing = trx.get("outgoing") or "-"
                amount = 0
                trxType = "debit"
                if incoming != "-" and float(incoming.replace(',', '')) > 0:
                    amount = float(incoming.replace(',', ''))
                    trxType = "credit"
                elif outgoing != "-" and float(outgoing.replace(',', '')) > 0:
                    amount = float(outgoing.replace(',', ''))
                    trxType = "debit"

                # convert date to timestamp
                try:
                    trx_datetime = datetime.strptime(trx.get("date"), "%b %d, %Y")  # Oct 17, 2025
                except Exception:
                    try:
                        trx_datetime = datetime.strptime(trx.get("date"), "%d-%b-%Y")  # 08-Sep-2025
                    except Exception:
                        trx_datetime = datetime.utcnow()  # fallback

                # generate hash
                trx_hash = calculate_trx_hash({"date": trx_datetime, "description": trx.get("description"), "amount": amount})

                # check duplicates
                cursor.execute('SELECT 1 FROM transactions WHERE "trxHash"=%s;', (trx_hash,))
                if cursor.fetchone():
                    continue  # skip duplicate

                # insert transaction
                cursor.execute("""
                    INSERT INTO transactions
                    ("trxNo", date, "trxDetail", amount, "trxType", "isTaxable", "userID", "accID", "categID", "trxHash")
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                """, (
                    trx.get("transaction_id") or None,
                    trx_datetime,
                    trx.get("description"),
                    amount,
                    trxType,
                    None,
                    user_id,
                    accID,
                    1,          # default category
                    trx_hash
                ))
                total_inserted += 1

            # insert into file_uploads table
            cursor.execute("""
                INSERT INTO file_uploads
                (filename, file_type, uploaded_at, total_transactions, "userID", "accID")
                VALUES (%s, %s, %s, %s, %s, %s);
            """, (
                file_info["filename"],
                file_info["file_type"],
                datetime.utcnow(),
                total_inserted,
                user_id,
                accID
            ))

            # commit all changes
            conn.commit()
    except Exception as e:
        conn.rollback()
        raise e

@router.post("/upload")
async def upload_file(background_tasks: BackgroundTasks,
                      curr_user: dict = Depends(get_current_user),
                      conn = Depends(connect_to_db),
                      file:UploadFile = File(...),
                      password: str | None = Form(None),
                      file_type: str = Form(...)
                      bank_name: str = Form(...)
                      ): 
    file_info = {"filename": file.filename, "file_type":file_type}
    complete_transactions=[]
    file_path=None
    total_no_pages=0
    account_number=None
    ubl_last_balance = None
    alfalah_last_balance = None
    try:
        file_type=detect_file_type(file.content_type)
        file_type["filename"]=file.filename
        file_path=save_temp_file(file)
        # --- Try extracting PDF text ---
        try:
            text, total_no_pages = extract_pdf_with_ocr(
                file_path,
                password=password
            )
        except ValueError as e:
            # Password related errors
            return JSONResponse(
                status_code=401,
                content={
                    "status": "PASSWORD_REQUIRED",
                    "message": str(e)
                }
            )
        #till here
        # if "easypaisa" in text:
        if bank_name=="easypaisa":    
            for i in range(1,total_no_pages+1):
                raw_file_path=f'output{i}.txt'
                transactions,acc_no=extract_transaction_of_easypaisa(filepath=raw_file_path,page_no=i,total_no_pages=total_no_pages,extract_account=(i == 1))
                if acc_no:
                    account_number = acc_no
                complete_transactions+=transactions
        elif bank_name=="meezan":   #first format of meezan bank statement , First page is not necessary so exclude.
            print("meezan bank detected")
            for i in range(2,total_no_pages+1):
                raw_file_path=f'output{i}.txt'
                transactions,acc_no=extract_transaction_of_meezan(filepath=raw_file_path,page_no=i,total_no_pages=total_no_pages,extract_account=(i == 2))
                if acc_no:
                    account_number = acc_no
                complete_transactions+=transactions  
        # print(complete_transactions)
        elif bank_name=="ubl":
            for i in range(1,total_no_pages+1):
                raw_file_path=f'output{i}.txt'
                transactions,acc_no,ubl_last_balance=extract_transaction_of_ubl(filepath=raw_file_path,page_no=i,total_no_pages=total_no_pages,extract_account=(i == 1),previous_balance=ubl_last_balance)
                if acc_no:
                    account_number = acc_no
                complete_transactions+=transactions
        elif bank_name=="alfalah":
            for i in range(1,total_no_pages+1):
                raw_file_path=f'output{i}.txt'
                transactions,acc_no,alfalah_last_balance=extract_transaction_of_alfalah(filepath=raw_file_path,page_no=i,total_no_pages=total_no_pages,extract_account=(i == 1),previous_balance=alfalah_last_balance)
                if acc_no:
                    account_number = acc_no
                complete_transactions+=transactions        

        else:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "UNSUPPORTED_BANK",
                    "message": "Unsupported bank statement."
                }
            )

        print(complete_transactions)

        with conn.cursor() as cursor:
            cursor.execute('SELECT "accID" FROM accounts WHERE "accountNo"=%s AND "userID"=%s;',
        (account_number, curr_user["userID"]))
            acc = cursor.fetchone()

        if not acc:
            raise HTTPException(
                status_code=403,
                detail="Account not found or not associated with user"
            )


        # run DB insert in background
        background_tasks.add_task(
            save_transactions_to_db,
            complete_transactions,
            account_number,
            curr_user["userID"],
            file_info,
            conn
        )

        return {"message": "File is being processed in the background", "account": account_number}
    
    finally:
        if file_path:
            delete_temp_file(file_path)
        for i in range(1,total_no_pages+1):   #delete raw text files
            raw_file_path=f'output{i}.txt'
            delete_temp_file(raw_file_path) 
        await file.close()       


# add account
@router.post('/new_account')
def new_acc(
    new_acc: NewAccount,
    curr_user: dict = Depends(get_current_user),
    conn = Depends(connect_to_db)
):
    with conn.cursor() as cursor:

        # get bankID from banks table
        cursor.execute(
            'SELECT "bankID" FROM banks WHERE name = %s;',
            (new_acc.bank,)
        )
        bank = cursor.fetchone()

        if not bank:
            raise HTTPException(
                status_code=404,
                detail="Bank not found"
            )

        bank_id = bank["bankID"]

        #check if account already exists (same bank + account number)
        cursor.execute(
            """
            SELECT 1
            FROM accounts
            WHERE "bankID" = %s AND "accountNo" = %s;
            """,
            (bank_id, new_acc.acc_no)
        )
        existing_account = cursor.fetchone()

        if existing_account:
            raise HTTPException(
                status_code=409,
                detail="Account already exists"
            )

        # insert new account
        cursor.execute(
            """
            INSERT INTO accounts ("userID", "bankID", "accountNo")
            VALUES (%s, %s, %s)
            RETURNING "accID", "accountNo";
            """,
            (curr_user["userID"], bank_id, new_acc.acc_no)
        )

        account = cursor.fetchone()
        conn.commit()

        return {
            "message": "Account added successfully",
            "account": {
                "accID": account["accID"],
                "bank": new_acc.bank,
                "accountNo": account["accountNo"]
            }
        }
