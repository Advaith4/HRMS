import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.dependencies import get_current_user
from src.models import User
from src.services.rag.access_control import RAGAccessControl
from src.services.rag.chat_service import RAGChatService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rag", tags=["rag"])


class RAGChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    collections: list[str] = Field(default_factory=list)


class RAGSource(BaseModel):
    collection: str | None = None
    source: str | None = None
    filename: str | None = None
    chunk_index: int | None = None
    entity_id: str | None = None
    entity_type: str | None = None
    user_id: str | None = None
    source_collection: str | None = None
    distance: float | None = None


class RAGChatResponse(BaseModel):
    answer: str
    sources: list[RAGSource]
    collections_used: list[str]


def get_rag_chat_service() -> RAGChatService:
    return RAGChatService()


def get_rag_access_control() -> RAGAccessControl:
    return RAGAccessControl()


@router.post("/chat", response_model=RAGChatResponse)
def rag_chat(
    body: RAGChatRequest,
    current_user: User = Depends(get_current_user),
    service: RAGChatService = Depends(get_rag_chat_service),
    access_control: RAGAccessControl = Depends(get_rag_access_control),
):
    try:
        plan = access_control.build_plan(current_user, body.collections)
        logger.info(
            "RAG chat query user_id=%s role=%s collections=%s",
            current_user.id,
            current_user.role,
            plan.collections,
        )
        return service.answer(body.query, plan.collections, filters=plan.filters, user=current_user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("RAG chat failed")
        raise HTTPException(status_code=500, detail="RAG chat failed") from exc
