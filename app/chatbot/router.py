"""FastAPI router for the FINSURE assistant.

Endpoints:
    POST /api/v1/chatbot/ask    - ask a question
    GET  /api/v1/chatbot/health - quick liveness probe
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .agent import ask as agent_ask

router = APIRouter(prefix="/api/v1/chatbot", tags=["Chatbot"])


class ChatMessage(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    history: Optional[List[ChatMessage]] = Field(
        default=None,
        description="Recent turns for short-term context. The client should send "
        "the last ~6 messages to keep tokens bounded.",
    )


class ChatResponse(BaseModel):
    response: str


@router.post("/ask", response_model=ChatResponse)
async def ask(request: ChatRequest) -> ChatResponse:
    try:
        answer = await agent_ask(
            request.query,
            [m.model_dump() for m in (request.history or [])],
        )
        return ChatResponse(response=answer)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except RuntimeError as exc:
        # Missing API key, etc.
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=f"Chatbot failed to answer: {exc}",
        )


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}
