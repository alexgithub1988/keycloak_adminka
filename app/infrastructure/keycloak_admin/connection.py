"""Управление подключением и аутентификацией Keycloak."""

import logging
import os

from dotenv import load_dotenv
from keycloak import KeycloakAdmin, KeycloakOpenID

load_dotenv(override=True)

logger = logging.getLogger(__name__)

_DEFAULT_SERVER_URL = "http://localhost:8080/"
_MASTER_REALM = "master"


class KeycloakConnection:
    """Управление подключением к Keycloak и жизненным циклом токена."""

    def __init__(self, realm: str):
        self.realm = realm
        self.server_url = os.getenv("KEYCLOAK_SERVER_URL", _DEFAULT_SERVER_URL)

        self.oidc = KeycloakOpenID(
            server_url=self.server_url,
            realm_name=_MASTER_REALM,
            client_id=os.getenv("CLIENT_ID", "my_app"),
            client_secret_key=os.getenv("CLIENT_SECRET", ""),
        )

        self._token = self._get_token()
        self.admin = self.connection()

    def _get_token(self) -> dict:
        """Получение токена (Resource Owner Password Credentials)."""
        username = os.getenv("ADMIN_USERNAME", "admin")
        password = os.getenv("ADMIN_PASSWORD", "admin")
        return self.oidc.token(
            username=username, password=password, grant_type="password"
        )

    def _refresh_token(self) -> None:
        """Обновляет токен и пересоздаёт admin-объект."""
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
        """Создаёт KeycloakAdmin-инстанс с текущим токеном."""
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
