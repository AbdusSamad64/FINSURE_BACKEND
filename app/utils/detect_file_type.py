def detect_file_type(content_type:str):
    if not content_type:
        return {"error": "Missing content type"}
    if content_type =="application/pdf":
        return {"type":"pdf"}
    elif content_type.startswith("image/"):    
        return {"type":"image"}
    else:
        return {"error": "Unsupported file type", "type":content_type}