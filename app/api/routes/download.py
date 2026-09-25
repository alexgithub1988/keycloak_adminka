import os

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.infrastructure.audit_service import AuditService
from app.infrastructure.csv_adapter import CsvAdapter
from app.infrastructure.download_handler import (
    normalize_download_handler,
)
from app.infrastructure.models import SessionLocal

DOWNLOAD_DIR = "download_files"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/download")
def download_file(request: Request, realm: str, db: Session = Depends(get_db)):
    filename = "output.csv"
    file_path = os.path.join(DOWNLOAD_DIR, filename)
    users_list = normalize_download_handler(realm)

    # Динамически собираем все поля из всех пользователей
    all_fieldnames = [
        "username",
        "lastName",
        "firstName",
        "region_code",
        "municipality_id",
    ]
    for user in users_list:
        for key in user.keys():
            if key not in all_fieldnames:
                all_fieldnames.append(key)

    csv_adapter = CsvAdapter()
    csv_adapter.dicts_to_csv(
        dicts=users_list, fieldnames=all_fieldnames, filepath=DOWNLOAD_DIR
    )

    # Получаем email пользователя из сессии и IP-адрес
    user_email = request.session.get("user_email", "anonymous")
    client_ip = request.client.host

    # Read file content for audit
    with open(file_path, encoding="utf-8") as f:
        file_content = f.read()

    # Записываем операцию скачивания файла в аудит
    AuditService.create_record(
        db=db,
        action="DOWNLOAD_FILE",
        user_email=user_email,
        file_name=filename,
        file_content=file_content,  # Save content for file system storage
        realm=realm,
        ip_address=client_ip,
        result="SUCCESS",
        summary=f"Downloaded file with {len(users_list)} users",
    )

    return FileResponse(file_path, media_type="text/csv", filename=filename)
