import logging
import re
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from src.api.dependencies import require_roles
from src.database.connection import get_session
from src.models import User, USER_ROLES
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
    location: Optional[str] = None
    experience: Optional[str] = None

class UserUpdate(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None

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
@router.get("/users", response_model=List[UserOut])
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

@router.get("/policies", response_model=List[PolicyOut])
def list_policies(_current_user: User = Depends(admin_required)):
    POLICIES_DIR.mkdir(parents=True, exist_ok=True)
    policies = []
    for p in sorted(POLICIES_DIR.iterdir()):
        if p.is_file() and p.suffix.lower() in {".txt", ".md"}:
            try:
                content = p.read_text(encoding="utf-8")
                title = p.stem.replace("_", " ").title()
                policies.append(PolicyOut(filename=p.name, title=title, content=content))
            except Exception as e:
                logger.error("Failed to read policy file %s: %s", p, e)
    return policies

@router.post("/policies", response_model=PolicyOut, status_code=201)
def create_policy(req: PolicyCreate, _current_user: User = Depends(admin_required)):
    POLICIES_DIR.mkdir(parents=True, exist_ok=True)
    filename = _safe_filename(req.title)
    filepath = POLICIES_DIR / filename
    if filepath.exists():
        raise HTTPException(status_code=409, detail="A policy with a similar title/filename already exists")

    filepath.write_text(req.content, encoding="utf-8")

    # Sync to Chroma
    try:
        ingestion = IngestionService(ChromaService(), EmbeddingService())
        ingestion.ingest_file(
            filepath,
            collection="company_policies",
            source_id=f"company_docs:policies:{filepath.stem}",
            metadata={
                "doc_section": "policies",
                "doc_type": "company_document",
                "source_collection": "company_policies",
            },
            replace_existing=True,
        )
    except Exception as e:
        logger.error("Chroma RAG ingestion failed for policy %s: %s", filepath, e)

    return PolicyOut(filename=filename, title=req.title, content=req.content)

@router.put("/policies/{filename}", response_model=PolicyOut)
def update_policy(filename: str, req: PolicyCreate, _current_user: User = Depends(admin_required)):
    filepath = POLICIES_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Policy file not found")

    filepath.write_text(req.content, encoding="utf-8")

    # Sync to Chroma
    try:
        ingestion = IngestionService(ChromaService(), EmbeddingService())
        ingestion.ingest_file(
            filepath,
            collection="company_policies",
            source_id=f"company_docs:policies:{filepath.stem}",
            metadata={
                "doc_section": "policies",
                "doc_type": "company_document",
                "source_collection": "company_policies",
            },
            replace_existing=True,
        )
    except Exception as e:
        logger.error("Chroma RAG update failed for policy %s: %s", filepath, e)

    return PolicyOut(filename=filename, title=req.title, content=req.content)

@router.delete("/policies/{filename}")
def delete_policy(filename: str, _current_user: User = Depends(admin_required)):
    filepath = POLICIES_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Policy file not found")

    filepath.unlink()

    # Clear from Chroma
    try:
        chroma = ChromaService()
        chroma.delete_where("company_policies", {"source_id": f"company_docs:policies:{filepath.stem}"})
    except Exception as e:
        logger.error("Chroma RAG delete failed for policy %s: %s", filepath.stem, e)

    return {"message": "Policy deleted successfully"}

@router.post("/policies/{filename}/reindex")
def reindex_policy(filename: str, _current_user: User = Depends(admin_required)):
    filepath = POLICIES_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Policy file not found")

    try:
        ingestion = IngestionService(ChromaService(), EmbeddingService())
        ingestion.ingest_file(
            filepath,
            collection="company_policies",
            source_id=f"company_docs:policies:{filepath.stem}",
            metadata={
                "doc_section": "policies",
                "doc_type": "company_document",
                "source_collection": "company_policies",
            },
            replace_existing=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chroma RAG re-index failed: {str(e)}")

    return {"message": "Policy re-indexed successfully"}

# --- Employee Knowledge Routes ---
@router.get("/knowledge", response_model=List[KnowledgeOut])
def list_knowledge(_current_user: User = Depends(admin_required)):
    articles = []
    for category in ("onboarding", "training"):
        dir_path = Path("data/company_docs") / category
        dir_path.mkdir(parents=True, exist_ok=True)
        for p in sorted(dir_path.iterdir()):
            if p.is_file() and p.suffix.lower() in {".txt", ".md"}:
                try:
                    content = p.read_text(encoding="utf-8")
                    title = p.stem.replace("_", " ").title()
                    articles.append(KnowledgeOut(filename=p.name, category=category, title=title, content=content))
                except Exception as e:
                    logger.error("Failed to read knowledge file %s: %s", p, e)
    return articles

@router.post("/knowledge", response_model=KnowledgeOut, status_code=201)
def create_knowledge(req: KnowledgeCreate, _current_user: User = Depends(admin_required)):
    if req.category not in ("onboarding", "training"):
        raise HTTPException(status_code=400, detail="Category must be 'onboarding' or 'training'")

    dir_path = Path("data/company_docs") / req.category
    dir_path.mkdir(parents=True, exist_ok=True)
    filename = _safe_filename(req.title)
    filepath = dir_path / filename
    if filepath.exists():
        raise HTTPException(status_code=409, detail="A knowledge article with a similar title already exists")

    filepath.write_text(req.content, encoding="utf-8")

    # Sync to Chroma
    try:
        ingestion = IngestionService(ChromaService(), EmbeddingService())
        ingestion.ingest_file(
            filepath,
            collection="employee_knowledge",
            source_id=f"company_docs:{req.category}:{filepath.stem}",
            metadata={
                "doc_section": req.category,
                "doc_type": "company_document",
                "source_collection": "employee_knowledge",
            },
            replace_existing=True,
        )
    except Exception as e:
        logger.error("Chroma RAG ingestion failed for article %s: %s", filepath, e)

    return KnowledgeOut(filename=filename, category=req.category, title=req.title, content=req.content)

@router.put("/knowledge/{category}/{filename}", response_model=KnowledgeOut)
def update_knowledge(category: str, filename: str, req: PolicyCreate, _current_user: User = Depends(admin_required)):
    if category not in ("onboarding", "training"):
        raise HTTPException(status_code=400, detail="Category must be 'onboarding' or 'training'")

    filepath = Path("data/company_docs") / category / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Knowledge article not found")

    filepath.write_text(req.content, encoding="utf-8")

    # Sync to Chroma
    try:
        ingestion = IngestionService(ChromaService(), EmbeddingService())
        ingestion.ingest_file(
            filepath,
            collection="employee_knowledge",
            source_id=f"company_docs:{category}:{filepath.stem}",
            metadata={
                "doc_section": category,
                "doc_type": "company_document",
                "source_collection": "employee_knowledge",
            },
            replace_existing=True,
        )
    except Exception as e:
        logger.error("Chroma RAG update failed for article %s: %s", filepath, e)

    return KnowledgeOut(filename=filename, category=category, title=req.title, content=req.content)

@router.delete("/knowledge/{category}/{filename}")
def delete_knowledge(category: str, filename: str, _current_user: User = Depends(admin_required)):
    if category not in ("onboarding", "training"):
        raise HTTPException(status_code=400, detail="Category must be 'onboarding' or 'training'")

    filepath = Path("data/company_docs") / category / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Knowledge article not found")

    filepath.unlink()

    # Clear from Chroma
    try:
        chroma = ChromaService()
        chroma.delete_where("employee_knowledge", {"source_id": f"company_docs:{category}:{filepath.stem}"})
    except Exception as e:
        logger.error("Chroma RAG delete failed for article %s: %s", filepath.stem, e)

    return {"message": "Knowledge article deleted successfully"}

@router.post("/knowledge/{category}/{filename}/reindex")
def reindex_knowledge(category: str, filename: str, _current_user: User = Depends(admin_required)):
    if category not in ("onboarding", "training"):
        raise HTTPException(status_code=400, detail="Category must be 'onboarding' or 'training'")

    filepath = Path("data/company_docs") / category / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Knowledge article not found")

    try:
        ingestion = IngestionService(ChromaService(), EmbeddingService())
        ingestion.ingest_file(
            filepath,
            collection="employee_knowledge",
            source_id=f"company_docs:{category}:{filepath.stem}",
            metadata={
                "doc_section": category,
                "doc_type": "company_document",
                "source_collection": "employee_knowledge",
            },
            replace_existing=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chroma RAG re-index failed: {str(e)}")

    return {"message": "Knowledge article re-indexed successfully"}
