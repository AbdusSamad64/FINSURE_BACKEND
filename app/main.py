import logging
import os
import sys
from fastapi import FastAPI
from dotenv import load_dotenv

# Force logging to be visible in all environments
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

from app.api.v1 import data_retrieval, routes_files, auth, reports_manager, dashboards, banks, demo, two_factor
from app.chatbot.router import router as chatbot_router
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()


def _parse_allowed_origins() -> list[str]:
    raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173")
    origins = [origin.strip().rstrip("/") for origin in raw_origins.split(",") if origin.strip()]
    return origins or ["http://localhost:5173"]


app = FastAPI(title="FINSURE - Financial Insights API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_allowed_origins(),
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
app.include_router(two_factor.router)

app.include_router(data_retrieval.router)

app.include_router(reports_manager.router)

app.include_router(chatbot_router)

app.include_router(dashboards.router)

app.include_router(banks.router)

app.include_router(demo.router)


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


@app.on_event("startup")
async def _start_categorization_worker():
    """Start the background worker for LLM-based categorization."""
    import asyncio
    from app.categorization.worker import categorization_worker
    asyncio.create_task(categorization_worker())



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
