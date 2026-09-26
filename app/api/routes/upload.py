import os

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.infrastructure.audit_service import AuditService
from app.infrastructure.csv_handler_upload import upload_handler
from app.infrastructure.models import SessionLocal

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


UPLOAD_DIR = "upload_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/files/upload")
def get_files(
    request: Request,
    file: UploadFile = File(...),
    realm: str = Form(...),
    db: Session = Depends(get_db),
):
    """Загружаем файл и редиректим на главную страницу"""
    # Получаем IP-адрес клиента
    client_ip = request.client.host

    # Получаем email пользователя из сессии
    user_email = request.session.get("user_email", "anonymous")

    # Read file content for audit
    file_content = file.file.read()
    file.file.seek(0)  # Reset file pointer for normal processing

    file_location = os.path.join(UPLOAD_DIR, file.filename)
    if not file.filename.endswith(".csv"):
        # Записываем попытку загрузки недопустимого файла в аудит
        AuditService.create_record(
            db=db,
            action="UPLOAD_FILE",
            user_email=user_email,
            file_name=file.filename,
            file_content=file_content.decode(
                "utf-8"
            ),  # Save content for file system storage
            ip_address=client_ip,
            result="FAILED",
            summary="Attempted to upload non-CSV file",
        )
        return RedirectResponse(url="/?error=csv_only", status_code=303)

    with open(file_location, "wb") as buffer:
        buffer.write(file_content)

    result = upload_handler(filepath=file_location, realm=realm)

    # Определяем результат операции для аудита
    total_processed = result["created"] + result["updated"]
    if total_processed == 0:
        audit_result = "FAILED"
        summary = f"Upload failed: 0 users processed, {result['skipped']} skipped"
    elif result["skipped"] > 0:
        audit_result = "PARTIAL_SUCCESS"
        summary = f"Upload partially successful: {result['created']} created, {result['updated']} updated, {result['skipped']} skipped"
    else:
        audit_result = "SUCCESS"
        summary = f"Upload successful: {result['created']} created, {result['updated']} updated, {result['skipped']} skipped"

    # Записываем операцию загрузки файла в аудит
    AuditService.create_record(
        db=db,
        action="UPLOAD_FILE",
        user_email=user_email,
        file_name=file.filename,
        file_content=file_content.decode(
            "utf-8"
        ),  # Save content for file system storage
        summary=summary,
        realm=realm,
        ip_address=client_ip,
        result=audit_result,
    )

    if total_processed == 0:
        # Ни одного пользователя не создано/обновлено
        return RedirectResponse(
            url=f"/?error=all_failed&created=0&updated=0&skipped={result['skipped']}&realm={realm}",
            status_code=303,
        )

    if result["skipped"] > 0 and total_processed > 0:
        # Частичный успех — показываем warning со статистикой
        return RedirectResponse(
            url=f"/?warning=partial_success&created={result['created']}&updated={result['updated']}&skipped={result['skipped']}&realm={realm}",
            status_code=303,
        )

    # Полное обновление — показываем success
    return RedirectResponse(
        url=f"/?success=upload_complete&created={result['created']}&updated={result['updated']}&skipped={result['skipped']}&realm={realm}",
        status_code=303,
    )
