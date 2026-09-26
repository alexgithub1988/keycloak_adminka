import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.infrastructure.audit_service import AuditService
from app.infrastructure.models import SessionLocal

router = APIRouter()

templates = Jinja2Templates(directory=Path(__file__).parent.parent.parent / "templates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/audit/history")
def get_audit_history(request: Request, db: Session = Depends(get_db)):
    """Получает историю аудита и отображает на странице"""

    # Get audit records
    audit_records = AuditService.get_history(db, limit=100)

    return templates.TemplateResponse(
        request, "audit.html", {"audit_records": audit_records}
    )


@router.get("/download/file/{record_id}")
def download_audit_file(record_id: int, db: Session = Depends(get_db)):
    """Скачивание файла из аудит-записи"""

    # Get audit record
    record = AuditService.get_record_by_id(db, record_id)
    if not record or not record.file_path:
        raise HTTPException(status_code=404, detail="File not found")

    # Check if file exists
    if not os.path.exists(record.file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    # Return file for download
    return FileResponse(
        path=record.file_path,
        filename=record.file_name,
        media_type="application/octet-stream",
    )
