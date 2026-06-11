from fastapi import APIRouter, Depends, Query

from app.core.database import Database
from app.dependencies import get_current_user, get_database
from app.schemas import AuditLogResponse


router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditLogResponse])
def list_audit_logs(
    limit: int = Query(default=50, ge=1, le=500),
    current_user: str = Depends(get_current_user),
    database: Database = Depends(get_database),
) -> list[dict]:
    return database.list_audit_logs(current_user, limit)
