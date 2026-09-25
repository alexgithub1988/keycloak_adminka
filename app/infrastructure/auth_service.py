import logging
import os

import jwt
from dotenv import load_dotenv
from jwt import PyJWKClient
from keycloak import KeycloakOpenID

load_dotenv(override=True)


class AuthService:
    """Сервис для авторизации через Keycloak OAuth2/OIDC."""

    def __init__(self):
        self.server_url = os.getenv("KEYCLOAK_URL", "http://localhost:8080/")
        if not self.server_url.endswith("/"):
            self.server_url = self.server_url + "/"
        self.realm = os.getenv("KC_REALM", "max")  # Use configured realm from .env
        self.client_id = os.getenv("CLIENT_ID", "my_app")
        self.client_secret = os.getenv("CLIENT_SECRET", "")

        self.oidc = KeycloakOpenID(
            server_url=self.server_url,
            realm_name=self.realm,
            client_id=self.client_id,
            client_secret_key=self.client_secret,
        )

        # Кэшируем PyJWKClient — создаём один раз, не пересоздаём при каждом вызове
        self._jwks_client = PyJWKClient(
            f"{self.server_url}realms/{self.realm}/protocol/openid-connect/certs"
        )

    def get_authorization_url(
        self, redirect_uri: str, state: str = "", prompt: str = ""
    ) -> str:
        """Генерирует URL для авторизации в Keycloak."""
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

        import urllib.parse

        query_string = urllib.parse.urlencode(params)
        auth_url = f"{self.server_url}realms/{self.realm}/protocol/openid-connect/auth?{query_string}"
        return auth_url

    def validate_state(self, stored_state: str, provided_state: str) -> bool:
        """Проверяет state для защиты от CSRF атак."""
        if not stored_state or not provided_state:
            return False
        return stored_state == provided_state

    def exchange_code_for_token(self, code: str, redirect_uri: str) -> dict:
        """Обменивает authorization code на access token."""
        try:
            # ВАЖНО: обязательно передавать grant_type и code именованными
            # параметрами. У KeycloakOpenID.token() позиционный аргумент
            # соответствует username, а grant_type по умолчанию "password" —
            # если передать code позиционно, запрос уйдёт как password-grant
            # с username=<code> и вызовет invalid_grant: Invalid user credentials.
            token = self.oidc.token(
                grant_type="authorization_code", code=code, redirect_uri=redirect_uri
            )
            return token
        except Exception as e:
            logging.error(f"Ошибка обмена code на token: {e}")
            raise

    def get_user_info(self, access_token: str) -> dict:
        """Получает информацию о пользователе из ID token с верификацией подписи."""
        try:
            # Получаем ключ из кэшированного JWKS (автоматически по kid из токена)
            signing_key = self._jwks_client.get_signing_key_from_jwt(access_token)

            # Декодируем токен с проверкой подписи и audience
            user_info = jwt.decode(
                access_token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.client_id,  # проверяем, что токен для нашего клиента
            )
            return user_info
        except Exception as e:
            logging.error(f"Ошибка верификации токена: {e}")
            return {}

    def get_logout_url(self, redirect_uri: str) -> str:
        """Генерирует URL для выхода."""
        import urllib.parse

        params = {
            "post_logout_redirect_uri": redirect_uri,
            "client_id": self.client_id,
        }
        query_string = urllib.parse.urlencode(params)
        logout_url = f"{self.server_url}realms/{self.realm}/protocol/openid-connect/logout?{query_string}"
        return logout_url

    def get_refresh_token(self, refresh_token: str) -> dict:
        """Обновляет access token используя refresh token."""
        try:
            token = self.oidc.refresh_token(refresh_token)
            return token
        except Exception as e:
            logging.error(f"Ошибка обновления токена: {e}")
            raise


# Глобальный экземпляр
auth_service = AuthService()
