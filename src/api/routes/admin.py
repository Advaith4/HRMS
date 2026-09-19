import logging
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from src.api.dependencies import require_roles
from src.database.connection import get_session
from src.models import USER_ROLES, User
from src.models import USER_ROLES, CompanyDocument, User
from src.services.rag.chroma_service import ChromaService
from src.services.rag.embedding_service import EmbeddingService
from src.services.rag.ingestion_service import IngestionService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])

# Limit access strictly to admin role
admin_required = require_roles("admin")

# --- Schemas ---
class UserOut(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool
    location: str | None = None
    experience: str | None = None

class UserUpdate(BaseModel):
    role: str | None = None
    is_active: bool | None = None

class PolicyOut(BaseModel):
    filename: str
    title: str
    content: str

class PolicyCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1)

class KnowledgeOut(BaseModel):
    filename: str
    category: str
    title: str
    content: str

class KnowledgeCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., min_length=1, max_length=50)  # "onboarding" or "training"
    content: str = Field(..., min_length=1)

def _safe_filename(title: str) -> str:
    cleaned = title.lower().strip().replace(" ", "_")
    cleaned = re.sub(r"[^\w_]", "", cleaned)
    if not cleaned:
        cleaned = "untitled"
    return f"{cleaned}.txt"

# --- User Routes ---
@router.get("/users", response_model=list[UserOut])
def list_users(
    session: Session = Depends(get_session),
    _current_user: User = Depends(admin_required)
):
    users = session.exec(select(User).order_by(User.id.asc())).all()
    return [
        UserOut(
            id=u.id,
            username=u.username,
            role=u.role,
            is_active=getattr(u, "is_active", True),
            location=u.location,
            experience=u.experience
        )
        for u in users
    ]

@router.put("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    req: UserUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(admin_required)
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot modify your own admin role or status")
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if req.role is not None:
        if req.role.lower() not in USER_ROLES:
            raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of {USER_ROLES}")
        user.role = req.role.lower()

    if req.is_active is not None:
        user.is_active = req.is_active

    session.add(user)
    session.commit()
    session.refresh(user)
    return UserOut(
        id=user.id,
        username=user.username,
        role=user.role,
        is_active=getattr(user, "is_active", True),
        location=user.location,
        experience=user.experience
    )

# --- Policy Routes ---
POLICIES_DIR = Path("data/company_docs/policies")

@router.get("/policies", response_model=list[PolicyOut])
def list_policies(session: Session = Depends(get_session), _current_user: User = Depends(admin_required)):
    docs = session.exec(select(CompanyDocument).where(CompanyDocument.category == "policies")).all()
    return [PolicyOut(filename=doc.filename, title=doc.title, content=doc.content) for doc in docs]

@router.post("/policies", response_model=PolicyOut, status_code=201)
def create_policy(req: PolicyCreate, session: Session = Depends(get_session), _current_user: User = Depends(admin_required)):
    filename = _safe_filename(req.title)
    existing = session.exec(select(CompanyDocument).where(CompanyDocument.category == "policies", CompanyDocument.filename == filename)).first()
    if existing:
        raise HTTPException(status_code=409, detail="A policy with a similar title/filename already exists")

    doc = CompanyDocument(
        category="policies",
        title=req.title,
        filename=filename,
        content=req.content
    )
    session.add(doc)
    session.commit()

    # Sync to Chroma
    try:
        ingestion = IngestionService(ChromaService(), EmbeddingService())
        ingestion.ingest_text(
            text=req.content,
            collection="company_policies",
            source_id=f"company_docs:policies:{filename}",
            metadata={
                "doc_section": "policies",
                "doc_type": "company_document",
                "source_collection": "company_policies",
            },
            replace_existing=True,
        )
    except Exception as e:
        logger.error("Chroma RAG update failed for policy %s: %s", filename, e)

    return PolicyOut(filename=filename, title=req.title, content=req.content)

@router.put("/policies/{filename}", response_model=PolicyOut)
def update_policy(filename: str, req: PolicyCreate, session: Session = Depends(get_session), _current_user: User = Depends(admin_required)):
    doc = session.exec(select(CompanyDocument).where(CompanyDocument.category == "policies", CompanyDocument.filename == filename)).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Policy file not found")

    doc.content = req.content
    session.add(doc)
    session.commit()

    # Sync to Chroma
    try:
        ingestion = IngestionService(ChromaService(), EmbeddingService())
        ingestion.ingest_text(
            text=req.content,
            collection="company_policies",
            source_id=f"company_docs:policies:{filename}",
            metadata={
                "doc_section": "policies",
                "doc_type": "company_document",
                "source_collection": "company_policies",
            },
            replace_existing=True,
        )
    except Exception as e:
        logger.error("Chroma RAG update failed for policy %s: %s", filename, e)

    return PolicyOut(filename=filename, title=req.title, content=req.content)

@router.delete("/policies/{filename}")
def delete_policy(filename: str, session: Session = Depends(get_session), _current_user: User = Depends(admin_required)):
    doc = session.exec(select(CompanyDocument).where(CompanyDocument.category == "policies", CompanyDocument.filename == filename)).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Policy file not found")

    session.delete(doc)
    session.commit()

    # Clear from Chroma
    try:
        chroma = ChromaService()
        chroma.delete_where("company_policies", {"source_id": f"company_docs:policies:{filename}"})
    except Exception as e:
        logger.error("Chroma RAG delete failed for policy %s: %s", filename, e)

    return {"message": "Policy deleted successfully"}

@router.post("/policies/{filename}/reindex")
def reindex_policy(filename: str, session: Session = Depends(get_session), _current_user: User = Depends(admin_required)):
    doc = session.exec(select(CompanyDocument).where(CompanyDocument.category == "policies", CompanyDocument.filename == filename)).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Policy file not found")

    try:
        ingestion = IngestionService(ChromaService(), EmbeddingService())
        ingestion.ingest_text(
            text=doc.content,
            collection="company_policies",
            source_id=f"company_docs:policies:{filename}",
            metadata={
                "doc_section": "policies",
                "doc_type": "company_document",
                "source_collection": "company_policies",
            },
            replace_existing=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chroma RAG re-index failed: {e!s}")

    return {"message": "Policy re-indexed successfully"}

# --- Employee Knowledge Routes ---
@router.get("/knowledge", response_model=list[KnowledgeOut])
def list_knowledge(session: Session = Depends(get_session), _current_user: User = Depends(admin_required)):
    docs = session.exec(select(CompanyDocument).where(CompanyDocument.category.in_(["onboarding", "training"]))).all()
    return [KnowledgeOut(filename=doc.filename, category=doc.category, title=doc.title, content=doc.content) for doc in docs]

@router.post("/knowledge", response_model=KnowledgeOut, status_code=201)
def create_knowledge(req: KnowledgeCreate, session: Session = Depends(get_session), _current_user: User = Depends(admin_required)):
    if req.category not in ("onboarding", "training"):
        raise HTTPException(status_code=400, detail="Category must be 'onboarding' or 'training'")

    filename = _safe_filename(req.title)
    existing = session.exec(select(CompanyDocument).where(CompanyDocument.category == req.category, CompanyDocument.filename == filename)).first()
    if existing:
        raise HTTPException(status_code=409, detail="A knowledge article with a similar title already exists")

    doc = CompanyDocument(
        category=req.category,
        title=req.title,
        filename=filename,
        content=req.content
    )
    session.add(doc)
    session.commit()

    # Sync to Chroma
    try:
        ingestion = IngestionService(ChromaService(), EmbeddingService())
        ingestion.ingest_text(
            text=req.content,
            collection="employee_knowledge",
            source_id=f"company_docs:{req.category}:{filename}",
            metadata={
                "doc_section": req.category,
                "doc_type": "company_document",
                "source_collection": "employee_knowledge",
            },
            replace_existing=True,
        )
    except Exception as e:
        logger.error("Chroma RAG ingestion failed for article %s: %s", filename, e)

    return KnowledgeOut(filename=filename, category=req.category, title=req.title, content=req.content)

@router.put("/knowledge/{category}/{filename}", response_model=KnowledgeOut)
def update_knowledge(category: str, filename: str, req: PolicyCreate, session: Session = Depends(get_session), _current_user: User = Depends(admin_required)):
    if category not in ("onboarding", "training"):
        raise HTTPException(status_code=400, detail="Category must be 'onboarding' or 'training'")

    doc = session.exec(select(CompanyDocument).where(CompanyDocument.category == category, CompanyDocument.filename == filename)).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Knowledge article not found")

    doc.content = req.content
    session.add(doc)
    session.commit()

    # Sync to Chroma
    try:
        ingestion = IngestionService(ChromaService(), EmbeddingService())
        ingestion.ingest_text(
            text=req.content,
            collection="employee_knowledge",
            source_id=f"company_docs:{category}:{filename}",
            metadata={
                "doc_section": category,
                "doc_type": "company_document",
                "source_collection": "employee_knowledge",
            },
            replace_existing=True,
        )
    except Exception as e:
        logger.error("Chroma RAG update failed for article %s: %s", filename, e)

    return KnowledgeOut(filename=filename, category=category, title=doc.title, content=req.content)

@router.delete("/knowledge/{category}/{filename}")
def delete_knowledge(category: str, filename: str, session: Session = Depends(get_session), _current_user: User = Depends(admin_required)):
    if category not in ("onboarding", "training"):
        raise HTTPException(status_code=400, detail="Category must be 'onboarding' or 'training'")

    doc = session.exec(select(CompanyDocument).where(CompanyDocument.category == category, CompanyDocument.filename == filename)).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Knowledge article not found")

    session.delete(doc)
    session.commit()

    # Clear from Chroma
    try:
        chroma = ChromaService()
        chroma.delete_where("employee_knowledge", {"source_id": f"company_docs:{category}:{filename}"})
    except Exception as e:
        logger.error("Chroma RAG delete failed for article %s: %s", filename, e)

    return {"message": "Knowledge article deleted successfully"}

@router.post("/knowledge/{category}/{filename}/reindex")
def reindex_knowledge(category: str, filename: str, session: Session = Depends(get_session), _current_user: User = Depends(admin_required)):
    if category not in ("onboarding", "training"):
        raise HTTPException(status_code=400, detail="Category must be 'onboarding' or 'training'")

    doc = session.exec(select(CompanyDocument).where(CompanyDocument.category == category, CompanyDocument.filename == filename)).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Knowledge article not found")

    try:
        ingestion = IngestionService(ChromaService(), EmbeddingService())
        ingestion.ingest_text(
            text=doc.content,
            collection="employee_knowledge",
            source_id=f"company_docs:{category}:{filename}",
            metadata={
                "doc_section": category,
                "doc_type": "company_document",
                "source_collection": "employee_knowledge",
            },
            replace_existing=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chroma RAG re-index failed: {e!s}")

    return {"message": "Knowledge article re-indexed successfully"}
