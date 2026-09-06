import os

from fastapi import APIRouter, File, UploadFile

from app.infrastructure.csv_handler_upload import upload_handler

router = APIRouter()


UPLOAD_DIR = "upload_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/files/upload")
def get_files(file: UploadFile = File(...)) -> dict:  # noqa  B008
    "Загружаем файл"
    file_location = os.path.join(UPLOAD_DIR, file.filename)
    if not file.filename.endswith(".csv"):
        return {"error": "Только CSV-файлы разрешены"}

    with open(file_location, "wb") as buffer:
        buffer.write(file.file.read())

    upload_handler(filepath=file_location, realm="master")

    return {"result": "Загрузка пользователей применена"}
