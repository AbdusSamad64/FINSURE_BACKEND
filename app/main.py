from fastapi import FastAPI
from app.api.v1 import data_retrieval, routes_files, auth
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="FINSURE - Financial Insights API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(
    routes_files.router,              # router object from routes_files.py
    prefix="/api/v1/files",           # base URL
    tags=["File Uploads"]             # optional, Swagger docs ke liye
)
app.include_router(auth.router)

app.include_router(data_retrieval.router)

@app.get("/", tags=["Root"])
def root():
    return JSONResponse(
        {
            "message": "Welcome to FINSURE Backend 🚀",
            "upload_endpoint": "http://127.0.0.1:8000/api/v1/files/upload",
            "docs": "http://127.0.0.1:8000/docs"
        }
    )