"""CRUD-операции с пользователями Keycloak."""

import logging

logger = logging.getLogger(__name__)


class UserRepository:
    """Операции над пользователями: создание, обновление, поиск, список."""

    def __init__(self, connection):
        self._conn = connection

    def check_token(self):
        self._conn.check_token()

    @property
    def admin(self):
        return self._conn.admin

    def create_user(
        self,
        email: str,
        username: str,
        enabled: bool,
        firstname: str,
        lastname: str,
    ) -> dict | None:
        """Создаёт пользователя с basic полями. Возвращает dict с ID или None."""
        self.check_token()
        try:
            payload = {
                "email": email,
                "username": username,
                "enabled": enabled,
                "firstName": firstname,
                "lastName": lastname,
            }
            new_user = self.admin.create_user(payload)
            logger.info(f"Пользователь с почтой {email} создан")
            return new_user
        except Exception as e:
            logger.error(f"Ошибка создания пользователя {email}: {e}")
            return None

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
            user_repr = self.admin.get_user(user_id)
            user_repr.update(
                email=email,
                username=username,
                firstName=firstname,
                lastName=lastname,
                enabled=enabled,
            )
            self.admin.update_user(user_id, user_repr)
            logger.info(f"Базовая информация пользователя {user_id} обновлена")
            return True
        except Exception as e:
            logger.error(f"Ошибка обновления пользователя {user_id}: {e}")
            return False

    def get_users(self) -> list:
        """Получает список всех пользователей."""
        self.check_token()
        try:
            return self.admin.get_users({})
        except Exception as e:
            logger.error(f"Не удалось получить список пользователей: {e}")
            return []

    def find_user(
        self, email: str, username: str, firstname: str, lastname: str
    ) -> dict | None:
        """Находит пользователя по email/username + name-критериям."""
        try:
            results = self.admin.get_users(
                {"email": email, "first_name": firstname, "last_name": lastname}
            )
            for user in results:
                if user.get("email") == email or user.get("username") == username:
                    return user
            return None
        except Exception as e:
            logger.error(f"Ошибка поиска пользователя (email={email}): {e}")
            return None
