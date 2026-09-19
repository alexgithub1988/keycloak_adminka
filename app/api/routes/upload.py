import os

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse

from app.infrastructure.csv_handler_upload import upload_handler

router = APIRouter()

UPLOAD_DIR = "upload_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/files/upload")
def get_files(request: Request, file: UploadFile = File(...), realm: str = Form(...)):  # noqa: B008
    """Загружаем файл и редиректим на главную страницу"""
    file_location = os.path.join(UPLOAD_DIR, file.filename)
    if not file.filename.endswith(".csv"):
        return RedirectResponse(url="/?error=csv_only", status_code=303)

    with open(file_location, "wb") as buffer:
        buffer.write(file.file.read())

    result = upload_handler(filepath=file_location, realm=realm)

    total_processed = result["created"] + result["updated"]
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
