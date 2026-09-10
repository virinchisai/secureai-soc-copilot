import csv
import io

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

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


@router.get("/export")
def export_audit_logs(
    limit: int = Query(default=1000, ge=1, le=5000),
    current_user: str = Depends(get_current_user),
    database: Database = Depends(get_database),
) -> StreamingResponse:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "id",
            "created_at",
            "username",
            "status",
            "source_count",
            "uploaded_files",
            "question",
            "response_summary",
        ],
    )
    writer.writeheader()
    for record in database.list_audit_logs_for_export(current_user, limit):
        writer.writerow(
            {
                **record,
                "uploaded_files": "; ".join(record["uploaded_files"]),
            }
        )

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                'attachment; filename="secureai-soc-copilot-audit.csv"'
            )
        },
    )
