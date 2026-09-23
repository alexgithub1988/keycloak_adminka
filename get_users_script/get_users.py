import asyncio
import os
import pathlib
from dataclasses import dataclass
from functools import wraps
from getpass import getpass

import pandas as pd
import requests
from dotenv import load_dotenv
from keycloak import KeycloakAdmin, KeycloakOpenID, KeycloakOpenIDConnection
from requests.cookies import RequestsCookieJar
from tqdm import tqdm

load_dotenv(override=True)


class HTTPOtpUnauthorizedError(Exception):
    def __str__(self):
        return "Неверная пара логин/пароль для HTTP OTP."


class HTTPOtpUnexpectedError(Exception):
    def __str__(self):
        return "Произошла неизвестная ошибка при попытке аутентифицироваться в HTTP OTP"


class HTTPUnableFetchError(Exception):
    def __str__(self):
        return "Произошла неизвестная ошибка при попытке аутентифицироваться в HTTP OTP"


@dataclass(frozen=True)
class Config:
    server_url: str = os.getenv(
        "KC_SERVER_URL", "https://predict-keycloak-k8s.adtech.vk.team"
    )
    admin_client_id: str = os.getenv("KC_ADMIN_CLIENT_ID", "admin-cli")
    admin_client_secret: str = os.getenv("KC_ADMIN_CLIENT_SECRET")
    realm: str | None = os.getenv("KC_REALM")


@dataclass
class OTPUser:
    username: str
    password: str


class HttpOTPAuth:
    def __init__(self, session: requests.Session, server_url: str) -> None:
        self.session = session
        self.server_url = server_url

    @property
    def http_otp_url(self) -> str:
        return f"{self.server_url}/httpotp/sign_in"

    @staticmethod
    def _create_otp_user() -> OTPUser:
        username = os.getenv("OTP_USERNAME")
        if username is None:
            username = input("Input domain username:\n>>> ")

        pin = os.getenv("OTP_PIN")
        if pin is None:
            pin = getpass("Введите pin (6 цифр):\n>>> ")

        if not username:
            raise ValueError("Доменное имя пользователя не было указано")

        if not pin:
            raise ValueError("Пароль в связке PIN + OTP не был указан")

        otp_code = getpass("Введите код с TOTP токена (6 цифр):\n>>> ")
        user = OTPUser(username=username, password=pin + otp_code)
        return user

    def auth(self) -> RequestsCookieJar:
        """Запускается процесс аутенификации в интерактивном режиме"""

        user = self._create_otp_user()

        response = self.session.get(
            self.http_otp_url,
            auth=(user.username, user.password),
        )

        if response.status_code == 401:
            raise HTTPOtpUnauthorizedError

        if response.status_code != 200:
            raise HTTPOtpUnexpectedError

        headers = response.headers
        x_auth_user_header = headers.get("X-Auth-User")
        x_auth_session = headers.get("X-Auth-Session")
        auth_cookie = response.cookies.get("pAuth")

        if x_auth_user_header != user.username:
            raise HTTPOtpUnauthorizedError

        if not x_auth_session:
            raise HTTPOtpUnauthorizedError

        if not auth_cookie:
            raise HTTPOtpUnauthorizedError

        return response.cookies


class CustomKeycloakOpenIDConnection(KeycloakOpenIDConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._http_otp_auth(self._s)

    @property
    def keycloak_openid(self) -> KeycloakOpenID:
        keycloak_openid = super().keycloak_openid
        http_otp_cookie = {"pAuth": self._s.cookies.get("pAuth")}

        keycloak_openid.connection._s.cookies.update(http_otp_cookie)

        # TODO: Для async_s не работает добавление http otp куки. Соответственно, интеграция с HTTP OTP невозможна.
        keycloak_openid.connection.async_s.cookies.update(http_otp_cookie)

        self.async_s.cookies.update(http_otp_cookie)
        return keycloak_openid

    def _http_otp_auth(self, session: requests.Session):
        client = HttpOTPAuth(session, server_url=self.server_url)
        client.auth()


def with_authorized_api(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        kc_config = Config()
        connection = CustomKeycloakOpenIDConnection(
            server_url=kc_config.server_url,
            realm_name=kc_config.realm,
            client_id=kc_config.admin_client_id,
            client_secret_key=kc_config.admin_client_secret,
            max_retries=3,
        )
        return await func(
            *args, **kwargs, api_client=KeycloakAdmin(connection=connection)
        )

    return wrapper


def normalize_user(api_client: KeycloakAdmin, user: dict) -> dict:
    """
    Приводит "сырое" представление пользователя Keycloak (UserRepresentation)
    к плоскому словарю для последующей выгрузки в xlsx.

    Атрибуты и группы обрабатываются полностью динамически: никакой заранее
    известный список атрибутов/групп/ролей не хардкодится, т.к. для разных
    реалмов их состав может отличаться.
    """
    user_id = user.get("id")

    flat_user = {
        "id": user_id,
        "username": user.get("username"),
        "email": user.get("email"),
        "firstName": user.get("firstName"),
        "lastName": user.get("lastName"),
        "enabled": user.get("enabled"),
        "emailVerified": user.get("emailVerified"),
        "createdTimestamp": user.get("createdTimestamp"),
    }

    # Атрибуты пользователя разворачиваем в отдельные колонки "как есть"
    attributes = user.get("attributes") or {}
    for attr_name, attr_values in attributes.items():
        if isinstance(attr_values, list):
            flat_user[attr_name] = "; ".join(str(v) for v in attr_values)
        else:
            flat_user[attr_name] = attr_values

    # Группы пользователя (а вместе с ними и его роль/уровень доступа
    # в терминах бизнеса) забираем напрямую из Keycloak, без перевода
    # в человекочитаемые названия - соответствие "группа -> роль" может
    # быть разным для разных реалмов.
    try:
        groups = api_client.get_user_groups(user_id=user_id)
    except Exception as e:
        groups = []
        flat_user["Ошибка получения групп"] = str(e)

    group_paths = [group.get("path", group.get("name", "")) for group in groups]
    flat_user["groups"] = "; ".join(path.lstrip("/") for path in group_paths if path)

    return flat_user


def fetch_all_users(api_client: KeycloakAdmin) -> list[dict]:
    """
    Получает всех пользователей текущего реалма и нормализует их.

    KeycloakAdmin.get_users() в используемой версии python-keycloak сам
    постранично обходит всех пользователей, если вызвать без явных
    параметров first/max, поэтому дополнительная ручная пагинация не нужна.
    """
    raw_users = api_client.get_users()

    normalized_users = []
    for user in tqdm(raw_users, total=len(raw_users), desc="Получение пользователей"):
        normalized_users.append(normalize_user(api_client, user))

    return normalized_users


@with_authorized_api
async def main(api_client: KeycloakAdmin):
    kc_config = Config()

    users = fetch_all_users(api_client)

    if not users:
        print("В реалме не найдено ни одного пользователя.")
        return

    # Собираем полный набор колонок динамически по объединению ключей
    # всех пользователей, чтобы не потерять атрибуты, которые встречаются
    # не у всех пользователей.
    all_fieldnames: list[str] = []
    for user in users:
        for key in user.keys():
            if key not in all_fieldnames:
                all_fieldnames.append(key)

    df = pd.DataFrame(users, columns=all_fieldnames)

    default_filename = f"users_export_{kc_config.realm or 'realm'}.xlsx"
    output_path = input(
        f"Укажите абсолютный путь для сохранения xlsx файла с пользователями "
        f"(Enter - сохранить как {default_filename} в текущей директории):\n>>> "
    )

    if not output_path:
        output_path = str(pathlib.Path.cwd() / default_filename)

    path = pathlib.Path(output_path)
    with pd.ExcelWriter(path) as executor:
        df.to_excel(executor, index=False)

    print(f"Итого выгружено {len(users)} пользователей.")
    print(f"Файл сохранён: {path}")


if __name__ == "__main__":
    asyncio.run(main())
