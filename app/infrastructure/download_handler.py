import logging

from dotenv import load_dotenv

from app.infrastructure.keycloack_adapter import KeycloakAdminAdapter

load_dotenv(override=True)
logging.basicConfig(level="INFO")


def download_handler(realm: str) -> list:
    """Получаем список юзеров"""
    try:
        logging.info("Получаем список пользователей")
        admin = KeycloakAdminAdapter(realm)
        users = admin.get_users()
        logging.info(f"Список юзеров содержит {users}")
        return users
    except Exception as e:
        logging.error(f"Не удалось получить список пользователей. Ошибка {e}")
        return []
