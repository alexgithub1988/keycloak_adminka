import os

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.infrastructure.csv_adapter import CsvAdapter
from app.infrastructure.download_handler import (
    normalize_download_handler,
)

DOWNLOAD_DIR = "download_files"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

router = APIRouter()


@router.get("/download")
def download_file(realm: str):
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
    return FileResponse(file_path, media_type="text/csv", filename=filename)
