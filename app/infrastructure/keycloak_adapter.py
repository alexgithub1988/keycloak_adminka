import logging
import os

from dotenv import load_dotenv
from keycloak import KeycloakAdmin, KeycloakOpenID

load_dotenv(override=True)
logging.basicConfig(level="INFO")


class KeycloakAdminAdapter:
    def __init__(self, realm: str):
        """
        Инициализация адаптера
        """
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

        self.oidc = KeycloakOpenID(
            server_url="http://localhost:8080/",
            realm_name="master",  # тут важно логинимся в мастер реалме
            client_id="my_app",
            client_secret_key=os.getenv("CLIENT_SECRET"),
        )

        self._token = self._get_token()
        self.admin = self.connection()

    def _get_token(self) -> dict:
        """Получение токена"""
        self._token = self.oidc.token(
            username="admin",
            password="admin",
            grant_type="password",
        )
        return self._token

    def _refresh_token(self) -> None:
        """Нужно для вызова если токен протух"""
        self._get_token()
        self.admin = KeycloakAdmin(
            server_url="http://localhost:8080/",
            token=self._token,
            realm_name=self.realm,
            pool_maxsize=20,
        )

    def check_token(self) -> None:
        """Проверяем жив ли токен"""
        try:
            self.admin.get_server_info()
        except Exception as e:
            """Проверка связана ли ошибка с авторизацией"""
            if "401" in str(e) or "Unauthorized" in str(e):
                self._refresh_token()
            else:
                logging.error(f"Ошибка связанная с проверкой токена. Текст ошибки {e}")

    def connection(self) -> KeycloakAdmin:
        admin = KeycloakAdmin(
            server_url="http://localhost:8080/",
            token=self._token,
            realm_name=self.realm,
            pool_maxsize=20,
        )
        return admin

    def create_user(
        self, email: str, username: str, enabled: bool, firstname: str, lastname: str
    ) -> str | None:
        """Create user with basic fields. Возвращает ID созданного пользователя или None."""
        self.check_token()
        try:
            # Basic fields отправляем как есть
            payload = {
                "email": email,
                "username": username,
                "enabled": enabled,
                "firstName": firstname,
                "lastName": lastname,
            }
            new_user = self.admin.create_user(payload)
            logging.info(f"Пользователь с почтой {email} создан")
            return new_user
        except Exception as e:
            logging.error(f"Ошибка создания пользователя {email}: {e}")
            return None

    def set_user_attributes(self, user_id: str, attributes: dict) -> bool:
        """Устанавливает атрибуты пользователя (region_code, municipality_id и т.д.)."""
        self.check_token()
        try:
            # Форматируем атрибуты в формат Keycloak: {key: [value]}
            formatted_attrs = {}
            for k, v in attributes.items():
                if v:
                    formatted_attrs[k] = [v]
            if formatted_attrs:
                self.admin.set_user_attributes(user_id, formatted_attrs)
                logging.info(
                    f"Атрибуты пользователя {user_id} установлены: {list(formatted_attrs.keys())}"
                )
            return True
        except Exception as e:
            logging.error(f"Ошибка установки атрибутов пользователя {user_id}: {e}")
            return False

    def update_user_attributes(self, user_id: str, attributes: dict) -> bool:
        """Обновляет атрибуты пользователя (добавляет/переопределяет)."""
        self.check_token()
        try:
            # Получаем текущие атрибуты
            current_attrs = self.admin.get_user_attributes(user_id)
            if current_attrs is None:
                current_attrs = {}

            # Объединяем с новыми
            for k, v in attributes.items():
                if v:
                    current_attrs[k] = str(v)

            # Форматируем в формат Keycloak
            formatted_attrs = {}
            for k, v in current_attrs.items():
                formatted_attrs[k] = [v]
            if formatted_attrs:
                self.admin.set_user_attributes(user_id, formatted_attrs)
                logging.info(
                    f"Атрибуты пользователя {user_id} обновлены: {list(formatted_attrs.keys())}"
                )
            return True
        except Exception as e:
            logging.error(f"Ошибка обновления атрибутов пользователя {user_id}: {e}")
            return False

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
        self.check_token()
        try:
            userRepresentation = self.admin.get_user(user_id)
            userRepresentation["email"] = email
            userRepresentation["username"] = username
            userRepresentation["firstName"] = firstname
            userRepresentation["lastName"] = lastname
            userRepresentation["enabled"] = enabled

            self.admin.update_user(user_id, userRepresentation)
            logging.info(f"Базовая информация пользователя {user_id} обновлена")
            return True
        except Exception as e:
            logging.error(
                f"Ошибка обновления базовой информации пользователя {user_id}: {e}"
            )
            return False

    def get_users(self) -> list:
        """Get users lists"""
        self.check_token()
        try:
            users = self.admin.get_users({})
            return users
        except Exception as e:
            logging.error(f"Не удалось получить список пользователей. Ошибка {e}")
            return None

    def _extract_user_key(self, row: dict) -> str:
        """Извлекает ключ для поиска пользователя (email или username)."""
        # Пробуем email, если нет — username
        email = row.get("email")
        if email:
            return email
        return row.get("username", "")

    def _separate_basic_and_attributes(self, row: dict) -> tuple[dict, dict]:
        """Разделяет row на basic fields и атрибуты на основе хардкода."""
        basic = {}
        attributes = {}

        for key, value in row.items():
            if key in self.basic_fields:
                basic[key] = value
            elif key in self.attribute_fields:
                attributes[key] = value
            # Если поле не в списке — игнорируем (например, если это roles в будущем)

        return basic, attributes

    def create_or_update_user(self, row: dict) -> dict:
        """Создаёт или обновляет пользователя с basic fields и атрибутами.
        Возвращает: {'action': 'created' | 'updated' | 'error', 'details': str}
        """
        email = row.get("email", row.get("username", ""))
        username = row.get("username", email)
        enabled = row.get("enabled", True)
        firstname = row.get("firstname", row.get("firstName", ""))
        lastname = row.get("lastname", row.get("lastName", ""))

        basic, attributes = self._separate_basic_and_attributes(row)

        if not email:
            return {"action": "error", "details": "Отсутствует email/username"}

        # Ищем существующего пользователя
        users = self.admin.get_users(
            {"email": email, "first_name": firstname, "last_name": lastname}
        )
        existing_user = None
        for user in users:
            if user.get("email") == email or user.get("username") == username:
                existing_user = user
                break

        if existing_user:
            # Обновляем существующего пользователя
            user_id = existing_user["id"]

            # Обновляем basic info
            self.update_user_basic_info(
                user_id=user_id,
                email=email,
                username=username,
                firstname=firstname,
                lastname=lastname,
                enabled=enabled,
            )

            # Обновляем атрибуты
            if attributes:
                self.update_user_attributes(user_id=user_id, attributes=attributes)

            return {"action": "updated", "details": f"Пользователь {email} обновлён"}

        else:
            # Создаём нового пользователя
            result = self.create_user(
                email=email,
                username=username,
                enabled=enabled,
                firstname=firstname,
                lastname=lastname,
            )

            if result is None:
                return {
                    "action": "error",
                    "details": f"Ошибка создания пользователя {email}",
                }

            user_id = result["id"]

            # Устанавливаем атрибуты
            if attributes:
                self.set_user_attributes(user_id=user_id, attributes=attributes)

            return {"action": "created", "details": f"Пользователь {email} создан"}

    def create_from_list(self, list_of_dicts: list) -> dict:
        """Создаёт или обновляет пользователей из списка словарей.
        Возвращает: {'created': int, 'updated': int, 'skipped': int, 'errors': list[str]}
        """
        if not list_of_dicts:
            logging.warning("Получен пустой список для загрузки")
            return {"created": 0, "updated": 0, "skipped": 0, "errors": []}

        # Автоопределение формата CSV
        first_row = list_of_dicts[0]
        keys = set(first_row.keys())

        created = 0
        updated = 0
        skipped = 0
        errors = []

        if "email" in keys or "username" in keys:
            logging.info("Распознан формат CSV (email или username)")
            for row in list_of_dicts:
                user_key = self._extract_user_key(row)
                if not user_key:
                    logging.warning("Пропуск строки: отсутствует email/username")
                    skipped += 1
                    continue

                result = self.create_or_update_user(row)

                if result["action"] == "created":
                    created += 1
                    logging.info(f"Создан: {result['details']}")
                elif result["action"] == "updated":
                    updated += 1
                    logging.info(f"Обновлён: {result['details']}")
                else:
                    skipped += 1
                    errors.append(result["details"])
                    logging.warning(result["details"])
        else:
            logging.error(
                f"Неизвестный формат CSV. Ожидалось 'email' или 'username'. "
                f"Доступные поля в первом ряду: {list(first_row.keys())}"
            )
            return {
                "created": 0,
                "updated": 0,
                "skipped": 0,
                "errors": ["Неизвестный формат CSV"],
            }

        logging.info(
            f"Загрузка завершена: создано={created}, обновлено={updated}, "
            f"пропущено={skipped}, всего строк={len(list_of_dicts)}"
        )
        return {
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "errors": errors,
        }

    def get_realms_list(self) -> list:
        """получаем список реалмов"""
        realm_list_of_dicts = self.admin.get_realms()
        list_of_realms = [realm_dict["realm"] for realm_dict in realm_list_of_dicts]
        return list_of_realms
