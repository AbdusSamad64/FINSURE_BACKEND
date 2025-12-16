from fastapi import APIRouter, UploadFile, File,Form
from fastapi.responses import JSONResponse
from app.utils.file_helpers import detect_file_type,save_temp_file,delete_temp_file
from app.services.extract_text import extract_pdf_with_ocr
from app.services.extract_transactions import extract_transaction_of_easypaisa,extract_transaction_of_meezan
router=APIRouter()

@router.post("/upload")
async def upload_file(file:UploadFile = File(...),
                      password: str | None = Form(None)
                      ): 
    # print(file.filename)       
    # print(file.content_type) 
    complete_transactions=[]
    file_path=None
    total_no_pages=0
    account_number=None
    try:
        file_type=detect_file_type(file.content_type)
        file_type["filename"]=file.filename
        file_path=save_temp_file(file)
        # text,total_no_pages=extract_pdf_with_ocr(file_path)
        #added
        # --- Try extracting PDF text ---
        try:
            text, total_no_pages = extract_pdf_with_ocr(
                file_path,
                password=password
            )
        except ValueError as e:
            # 🔐 Password related errors
            return JSONResponse(
                status_code=401,
                content={
                    "status": "PASSWORD_REQUIRED",
                    "message": str(e)
                }
            )
        #till here
        if "easypaisa" in text:
            for i in range(1,total_no_pages+1):
                raw_file_path=f'output{i}.txt'
                transactions,acc_no=extract_transaction_of_easypaisa(filepath=raw_file_path,page_no=i,total_no_pages=total_no_pages,extract_account=(i == 1))
                if acc_no:
                    account_number = acc_no
                complete_transactions+=transactions
        elif "MEEZAN" in text:   #first format of meezan bank statement , First page is not necessary so exclude.
            print("meezan bank detected")
            for i in range(2,total_no_pages+1):
                raw_file_path=f'output{i}.txt'
                transactions,acc_no=extract_transaction_of_meezan(filepath=raw_file_path,page_no=i,total_no_pages=total_no_pages,extract_account=(i == 2))
                if acc_no:
                    account_number = acc_no
                complete_transactions+=transactions  
        # print(complete_transactions)
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "UNSUPPORTED_BANK",
                    "message": "Unsupported bank statement."
                }
            )

        return complete_transactions,account_number

    
    finally:
        if file_path:
            delete_temp_file(file_path)
        for i in range(1,total_no_pages+1):   #delete raw text files
            raw_file_path=f'output{i}.txt'
            delete_temp_file(raw_file_path) 
        await file.close()       
