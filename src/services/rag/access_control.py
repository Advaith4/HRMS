from dataclasses import dataclass

from src.models import User
from src.services.rag.chroma_service import DEFAULT_COLLECTIONS

PUBLIC_COLLECTIONS = ("company_policies", "job_descriptions")
PRIVATE_CANDIDATE_COLLECTIONS = ("candidate_profiles", "interview_reports")
HR_COLLECTIONS = DEFAULT_COLLECTIONS
HR_ROLES = {"hr", "admin", "manager"}


@dataclass(frozen=True)
class RAGAccessPlan:
    collections: list[str]
    filters: dict[str, dict]


class RAGAccessControl:
    def build_plan(self, user: User, requested_collections: list[str] | None = None) -> RAGAccessPlan:
        requested = requested_collections or []
        invalid = [collection for collection in requested if collection not in DEFAULT_COLLECTIONS]
        if invalid:
            raise ValueError(f"Unsupported RAG collection(s): {', '.join(invalid)}")

        allowed = self._allowed_collections(user)
        selected = requested or allowed
        denied = [collection for collection in selected if collection not in allowed]
        if denied:
            raise PermissionError(f"Unauthorized RAG collection(s): {', '.join(denied)}")

        filters: dict[str, dict] = {}
        if user.role == "candidate":
            user_filter = {"user_id": str(user.id)}
            for collection in PRIVATE_CANDIDATE_COLLECTIONS:
                if collection in selected:
                    filters[collection] = user_filter
        return RAGAccessPlan(collections=list(selected), filters=filters)

    def _allowed_collections(self, user: User) -> list[str]:
        if user.role in HR_ROLES:
            return list(HR_COLLECTIONS)
        if user.role == "candidate":
            return list(PUBLIC_COLLECTIONS + PRIVATE_CANDIDATE_COLLECTIONS)
        if user.role == "employee":
            return ["company_policies", "job_descriptions", "employee_knowledge"]
        return list(PUBLIC_COLLECTIONS)
