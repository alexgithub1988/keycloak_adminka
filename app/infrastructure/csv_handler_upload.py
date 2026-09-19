import logging
import os

from dotenv import load_dotenv

from app.infrastructure.csv_adapter import CsvAdapter
from app.infrastructure.keycloak_adapter import KeycloakAdminAdapter

load_dotenv(override=True)
logging.basicConfig(level="INFO")


def upload_handler(filepath: str, realm: str) -> dict:
    """Загружаем файл. Возвращает: {'created': int, 'updated': int, 'skipped': int, 'errors': list[str]}"""
    upload = KeycloakAdminAdapter(realm)
    csv_adapter = CsvAdapter()

    if not os.path.exists(filepath):
        logging.error(f"Файл {filepath} не найден")
        return {
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": [f"Файл {filepath} не найден"],
        }

    get_list = csv_adapter.get_list_dicts(filepath)

    logging.info("Загружаем юзеров")
    result = upload.create_from_list(get_list)

    total_processed = result["created"] + result["updated"]
    if result["skipped"] > 0:
        logging.warning(
            f"Часть пользователей не создана/обновлена: {result['skipped']} из {len(get_list)}"
        )

    return result
