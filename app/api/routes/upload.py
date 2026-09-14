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

    upload_handler(filepath=file_location, realm=realm)

    return RedirectResponse(url="/?success=upload_complete", status_code=303)
