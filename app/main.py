from fastapi import FastAPI
from app.api.v1 import data_retrieval, routes_files, auth, reports_manager
from app.chatbot.router import router as chatbot_router
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

app.include_router(reports_manager.router)

app.include_router(chatbot_router)


@app.on_event("startup")
async def _warmup_chatbot() -> None:
    """Build the chatbot's FAISS index at startup so the first user request is fast.
    Failures here are non-fatal - they surface when the user actually asks something
    so the rest of the API keeps working even if the guide PDF or API key is missing.
    """
    try:
        from app.chatbot.tools.info_tool import warmup

        warmup()
    except Exception as exc:  # noqa: BLE001
        print(f"[chatbot] warmup skipped: {exc}")


@app.get("/", tags=["Root"])
def root():
    return JSONResponse(
        {
            "message": "Welcome to FINSURE Backend 🚀",
            "upload_endpoint": "http://127.0.0.1:8000/api/v1/files/upload",
            "chatbot_endpoint": "http://127.0.0.1:8000/api/v1/chatbot/ask",
            "docs": "http://127.0.0.1:8000/docs"
        }
    )