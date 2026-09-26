"""Фасад для модуля keycloak_admin — полная обратная совместимость.

Все потребители (csv_handler_upload, download_handler, routes)
продолжают работать через тот же класс KeycloakAdminAdapter.
Вся бизнес-логика делегируется в подклассы keycloak_admin.
"""

import logging

from app.infrastructure.keycloak_admin.attribute_repository import AttributeRepository
from app.infrastructure.keycloak_admin.connection import KeycloakConnection
from app.infrastructure.keycloak_admin.csv_import_service import CsvImportService
from app.infrastructure.keycloak_admin.group_repository import GroupRepository
from app.infrastructure.keycloak_admin.user_repository import UserRepository

logger = logging.getLogger(__name__)


class KeycloakAdminAdapter:
    """Тонкий фасад над 5 классами keycloak_admin.

    Сохраняет полный публичный API оригинального KeycloakAdminAdapter,
    чтобы все consumers работали без изменений.
    """

    def __init__(self, realm: str):
        self.realm = realm

        # Хардкод: какие поля являются basic, а какие — атрибутами
        self.basic_fields = [
            "email",
            "username",
            "firstName",
            "lastName",
            "enabled",
            "emailVerified",
        ]
        self.attribute_fields = ["region_code", "municipality_id"]

        # Подклассы — создаются один раз в __init__
        self._conn = KeycloakConnection(realm)
        self._user_repo = UserRepository(self._conn)
        self._attr_repo = AttributeRepository(self._conn)
        self._group_repo = GroupRepository(self._conn)
        self._csv_service = CsvImportService(
            user_repo=self._user_repo,
            attr_repo=self._attr_repo,
            group_repo=self._group_repo,
            basic_fields=self.basic_fields,
            attribute_fields=self.attribute_fields,
        )

    # ---- Connection -------------------------------------------------------

    def check_token(self) -> None:
        """Проверяет жив ли токен. При 401 — обновляет."""
        self._conn.check_token()

    def get_realms_list(self) -> list:
        """Возвращает список имён реалмов."""
        return self._conn.get_realms_list()

    # ---- UserRepository ---------------------------------------------------

    def create_user(
        self,
        email: str,
        username: str,
        enabled: bool,
        firstname: str,
        lastname: str,
    ):
        """Создаёт пользователя с basic полями. Возвращает dict с ID или None."""
        return self._user_repo.create_user(
            email=email,
            username=username,
            enabled=enabled,
            firstname=firstname,
            lastname=lastname,
        )

    def update_user_basic_info(
        self,
        user_id: str,
        email: str,
        username: str,
        firstname: str,
        lastname: str,
        enabled: bool,
    ) -> bool:
        """Обновляет базовую информацию пользователя."""
        return self._user_repo.update_user_basic_info(
            user_id=user_id,
            email=email,
            username=username,
            firstname=firstname,
            lastname=lastname,
            enabled=enabled,
        )

    def get_users(self) -> list:
        """Получает список всех пользователей."""
        return self._user_repo.get_users()

    def find_user(
        self,
        email: str,
        username: str,
        firstname: str,
        lastname: str,
    ):
        """Находит пользователя по email/username + name-критериям."""
        return self._user_repo.find_user(
            email=email,
            username=username,
            firstname=firstname,
            lastname=lastname,
        )

    # ---- AttributeRepository ----------------------------------------------

    def set_user_attributes(self, user_id: str, attributes: dict) -> bool:
        """Устанавливает атрибуты пользователя."""
        return self._attr_repo.set_user_attributes(user_id, attributes)

    def update_user_attributes(self, user_id: str, attributes: dict) -> bool:
        """Обновляет атрибуты пользователя."""
        return self._attr_repo.update_user_attributes(user_id, attributes)

    # ---- CsvImportService -------------------------------------------------

    def create_or_update_user(self, row: dict) -> dict:
        """Создаёт или обновляет пользователя из словаря."""
        return self._csv_service.create_or_update_user(row)

    def create_from_list(self, list_of_dicts: list) -> dict:
        """Создаёт или обновляет пользователей из списка словарей."""
        try:
            return self._csv_service.create_from_list(list_of_dicts)
        except Exception as e:
            logger.error(f"Ошибка загрузки в реалм {self.realm}: {e}", exc_info=True)
            return {
                "created": 0,
                "updated": 0,
                "skipped": len(list_of_dicts) if list_of_dicts else 0,
                "errors": [f"Критическая ошибка при загрузке: {str(e)}"],
                "group_warnings": 0,
            }

    # ---- CsvImportService (доп) ------------------------------------------

    def get_users_with_groups(self) -> list:
        """Получает список пользователей вместе с группами."""
        return self._csv_service.get_users_with_groups()
