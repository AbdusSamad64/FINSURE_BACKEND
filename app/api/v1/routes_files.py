from fastapi import APIRouter, UploadFile, File
from app.utils.detect_file_type import detect_file_type

router=APIRouter()

@router.post("/upload")
async def upload_file(file:UploadFile = File(...)): 
    print(file.filename)       
    print(file.content_type) 
    # if file.content_type =="application/pdf":
    #     return {"filename": file.filename, "type": file.content_type,"PDF":True}
    # elif file.content_type.startswith("image/"):    
    #     return {"filename": file.filename, "type": file.content_type,"Image":True}
    # else:
    #     return {"error": "Unsupported file type", "type": file.content_type}
    file_type=detect_file_type(file.content_type)
    file_type["filename"]=file.filename
    return file_type

    
   
