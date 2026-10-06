"""Управление подключением и аутентификацией Keycloak.

Только одна переменная: KEYCLOAK_URL
- Для Docker: http://keycloak:8080
- Для локально (без Docker): http://localhost:8080

Для операций администрирования используем встроенный admin-cli клиент
с admin:admin (без пароля для admin-cli).
"""

import logging
import os

from keycloak import KeycloakAdmin, KeycloakOpenID

logger = logging.getLogger(__name__)

_DEFAULT_SERVER_URL = "http://localhost:8080/"
_MASTER_REALM = "master"
_ADMIN_CLIENT_ID = "admin-cli"


class KeycloakConnection:
    """Управление подключением к Keycloak и жизненным циклом токена."""

    def __init__(self, realm: str):
        self.realm = realm
        # Одна переменная KEYCLOAK_URL для всех операций
        self.server_url = os.getenv("KEYCLOAK_URL", _DEFAULT_SERVER_URL)
        if not self.server_url.endswith("/"):
            self.server_url = self.server_url + "/"

        # Для получения токена используем admin-cli клиент (встроенный в Keycloak)
        # с admin credentials (без секрета)
        self.oidc = KeycloakOpenID(
            server_url=self.server_url,
            realm_name=_MASTER_REALM,
            client_id=_ADMIN_CLIENT_ID,
            client_secret_key="",
        )

        self._token = self._get_token()
        self.admin = self.connection()

    def _get_token(self) -> dict:
        """Получение токена для admin-cli с admin:admin."""
        username = "admin"
        password = "admin"
        return self.oidc.token(
            username=username, password=password, grant_type="password"
        )

    def _refresh_token(self) -> None:
        """Обновляет токен и пересоздает admin-объект."""
        self._token = self._get_token()
        self.admin = self.connection()

    def check_token(self) -> None:
        """Проверяет жив ли токен. Если 401 — обновляет."""
        try:
            self.admin.get_server_info()
        except Exception as e:
            if "401" in str(e) or "Unauthorized" in str(e):
                self._refresh_token()
            else:
                logger.error(f"Ошибка проверки токена: {e}")

    def connection(self) -> KeycloakAdmin:
        """Создает KeycloakAdmin-инстанс с текущим токеном."""
        return KeycloakAdmin(
            server_url=self.server_url,
            token=self._token,
            realm_name=self.realm,
            pool_maxsize=20,
        )

    def get_realms_list(self) -> list:
        """Возвращает список имён реалмов (вызывается из master)."""
        self.check_token()
        try:
            realms_data = self.admin.get_realms()
            return [r["realm"] for r in realms_data]
        except Exception as e:
            logger.error(f"Не удалось получить список реалмов: {e}")
            return []
