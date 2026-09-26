import logging

from dotenv import load_dotenv

from app.infrastructure.keycloak_adapter import KeycloakAdminAdapter

load_dotenv(override=True)
logging.basicConfig(level="INFO")


def download_handler(realm: str) -> list:
    """Получаем список юзеров с группами."""
    try:
        logging.info("Получаем список пользователей")
        admin = KeycloakAdminAdapter(realm)
        users = admin.get_users_with_groups()
        logging.info(f"Список юзеров содержит {users}")
        return users
    except Exception as e:
        logging.error(f"Не удалось получить список пользователей. Ошибка {e}")
        return []


def normalize_download_handler(realm: str) -> list:
    users = download_handler(realm)
    normalized_users = []

    for user in users:
        normalized_user = user.copy()
        # Удаляем служебные поля
        for key in [
            "attributes",
            "notBefore",
            "disableableCredentialTypes",
            "requiredActions",
            "access",
            "totp",
            "createdTimestamp",
        ]:
            normalized_user.pop(key, None)
        normalized_users.append(normalized_user)

    return normalized_users
