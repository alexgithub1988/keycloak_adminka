import os

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.infrastructure.csv_adapter import CsvAdapter
from app.infrastructure.download_handler import (
    normalize_download_handler,
)

DOWNLOAD_DIR = "download_files"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


# settings
fieldnames = ["username", "lastName", "firstName", "is_test", "test2"]

router = APIRouter()


@router.get("/download")
def download_file(realm: str):
    filename = "output.csv"
    file_path = os.path.join(DOWNLOAD_DIR, filename)
    users_list = normalize_download_handler(realm)
    csv_adapter = CsvAdapter()
    csv_adapter.dicts_to_csv(
        dicts=users_list, fieldnames=fieldnames, filepath=DOWNLOAD_DIR
    )
    return FileResponse(file_path, media_type="text/csv", filename=filename)
