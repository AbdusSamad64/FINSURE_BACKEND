import os
from pathlib import Path
import shutil

def detect_file_type(content_type:str):
    if not content_type:
        return {"error": "Missing content type"}
    if content_type =="application/pdf":
        return {"type":"pdf"}
    elif content_type.startswith("image/"):    
        return {"type":"image"}
    else:
        return {"error": "Unsupported file type", "type":content_type}
    

UPLOAD_DIR = Path("uploads")

def save_temp_file(file):
#    Temporarily save uploaded file
    UPLOAD_DIR.mkdir(exist_ok=True)
    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return file_path

def delete_temp_file(file_path):
    """Delete file after processing"""
    try:
        os.remove(file_path)
    except Exception as e:
        print(f"File delete error: {e}")    

        