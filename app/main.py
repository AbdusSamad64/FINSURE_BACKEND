from fastapi import FastAPI
from app.api.v1 import routes_files
from fastapi.responses import JSONResponse

app = FastAPI(title="FINSURE - Financial Insights API")


app.include_router(
    routes_files.router,              # router object from routes_files.py
    prefix="/api/v1/files",           # base URL
    tags=["File Uploads"]             # optional, Swagger docs ke liye
)

@app.get("/", tags=["Root"])
def root():
    return JSONResponse(
        {
            "message": "Welcome to FINSURE Backend 🚀",
            "upload_endpoint": "http://127.0.0.1:8000/api/v1/files/upload",
            "docs": "http://127.0.0.1:8000/docs"
        }
    )