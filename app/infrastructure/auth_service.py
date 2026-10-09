import logging
import os
import urllib.parse

import jwt
from dotenv import load_dotenv
from jwt import PyJWKClient
from keycloak import KeycloakOpenID

load_dotenv(override=True)

logger = logging.getLogger(__name__)


class AuthService:
    """Сервис для авторизации через Keycloak OAuth2/OIDC.

    Одна переменная KEYCLOAK_URL для всех.
    Для браузера заменяем 'keycloak' на 'localhost' на лету.
    """

    def __init__(self):
        # Одна переменная для всего
        self.server_url = os.getenv("KEYCLOAK_URL", "http://localhost:8080/")
        if not self.server_url.endswith("/"):
            self.server_url = self.server_url + "/"

        self.realm = "master"
        self.client_id = os.getenv("CLIENT_ID", "my_app")
        self.client_secret = os.getenv("CLIENT_SECRET", "")

        logger.info(
            f"AuthService: server_url={self.server_url}, client_id={self.client_id}"
        )

        try:
            self.oidc = KeycloakOpenID(
                server_url=self.server_url,
                realm_name=self.realm,
                client_id=self.client_id,
                client_secret_key=self.client_secret,
            )
            logger.info("KeycloakOpenID initialized")
        except Exception as e:
            logger.error(f"Failed to initialize KeycloakOpenID: {e}")
            raise

        try:
            self._jwks_client = PyJWKClient(
                f"{self.server_url}realms/{self.realm}/protocol/openid-connect/certs"
            )
            logger.info("PyJWKClient initialized")
        except Exception as e:
            logger.error(f"Failed to initialize PyJWKClient: {e}")

    def _get_browser_url(self, url: str) -> str:
        """Заменяет 'keycloak' на 'localhost' для браузера.

        Внутри контейнера Keycloak = http://keycloak:8080,
        но браузер на хосте не может разрешить 'keycloak' —
        только 'localhost'.
        """
        return url.replace("keycloak", "localhost")

    def get_authorization_url(
        self, redirect_uri: str, state: str = "", prompt: str = ""
    ) -> str:
        """Генерирует URL для авторизации в Keycloak (для браузера)."""
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": "openid profile email",
        }
        if state:
            params["state"] = state
        if prompt:
            params["prompt"] = prompt

        query_string = urllib.parse.urlencode(params)
        auth_url = f"{self.server_url}realms/{self.realm}/protocol/openid-connect/auth?{query_string}"
        # Заменяем для браузера
        auth_url = self._get_browser_url(auth_url)
        logger.info(f"Authorization URL: {auth_url}")
        return auth_url

    def validate_state(self, stored_state: str, provided_state: str) -> bool:
        """Проверяет state для защиты от CSRF атак."""
        if not stored_state or not provided_state:
            return False
        return stored_state == provided_state

    def exchange_code_for_token(self, code: str, redirect_uri: str) -> dict:
        """Обменивает authorization code на access token."""
        return self.oidc.token(
            grant_type="authorization_code",
            code=code,
            redirect_uri=redirect_uri,
        )

    def get_user_info(self, id_token: str) -> dict:
        """Декодирует id_token и возвращает user info."""
        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(id_token)
            decoded = jwt.decode(
                id_token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.client_id,
            )
            return decoded
        except Exception as e:
            logger.error(f"Failed to decode id_token: {e}")
            return {}

    def get_logout_url(self, redirect_uri: str = "") -> str:
        """Генерирует URL для logout из Keycloak (для браузера)."""
        params = {"client_id": self.client_id}
        if redirect_uri:
            params["post_logout_redirect_uri"] = redirect_uri
        query_string = urllib.parse.urlencode(params)
        logout_url = (
            f"{self.server_url}realms/{self.realm}/protocol/openid-connect/logout"
            f"?{query_string}"
        )
        # Заменяем для браузера
        logout_url = self._get_browser_url(logout_url)
        return logout_url


auth_service = AuthService()
