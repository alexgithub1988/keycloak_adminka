import logging
import os

from dotenv import load_dotenv

from app.infrastructure.csv_adapter import CsvAdapter
from app.infrastructure.keycloack_adapter import KeycloakAdminAdapter

load_dotenv(override=True)
logging.basicConfig(level="INFO")


def upload_handler(filepath: str, realm: str):
    """Загружаем файл"""
    upload = KeycloakAdminAdapter(realm)
    csv_adapter = CsvAdapter()

    if not os.path.exists(filepath):
        logging.error(f"Файл {filepath} не найден")
        return

    get_list = csv_adapter.get_list_dicts(filepath)

    try:
        logging.info("Загружаем юзеров")
        upload.create_from_list(get_list)
    except Exception as e:
        logging.error(f"Ошибка при загрузке {e}")
