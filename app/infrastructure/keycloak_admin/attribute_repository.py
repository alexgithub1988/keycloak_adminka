"""Управление атрибутами пользователей Keycloak."""

import logging

logger = logging.getLogger(__name__)


class AttributeRepository:
    """CRUD-операции над атрибутами пользователей."""

    def __init__(self, connection):
        self._conn = connection

    def check_token(self):
        self._conn.check_token()

    @property
    def admin(self):
        return self._conn.admin

    @staticmethod
    def _normalize_attributes(attributes: dict) -> dict:
        """Приводит значения атрибутов к формату Keycloak: {name: [str, ...]}."""
        result: dict = {}
        for key, value in (attributes or {}).items():
            if value is None or value == "":
                continue
            if isinstance(value, list):
                values = [str(v) for v in value if v not in (None, "")]
            else:
                values = [str(value)]
            if values:
                result[key] = values
        return result

    def set_user_attributes(self, user_id: str, attributes: dict) -> bool:
        """Устанавливает пользовательские атрибуты из правил реалма."""
        self.check_token()
        try:
            formatted_attrs = self._normalize_attributes(attributes)
            if not formatted_attrs:
                return True

            user_repr = self.admin.get_user(user_id)
            user_repr["attributes"] = formatted_attrs
            self.admin.update_user(user_id, user_repr)
            logger.info(
                f"Атрибуты пользователя {user_id} установлены: {list(formatted_attrs.keys())}"
            )
            return True
        except Exception as e:
            logger.error(f"Ошибка установки атрибутов пользователя {user_id}: {e}")
            return False

    def update_user_attributes(self, user_id: str, attributes: dict) -> bool:
        """Обновляет атрибуты пользователя (добавляет/переопределяет)."""
        self.check_token()
        try:
            user_repr = self.admin.get_user(user_id)
            current_attrs = self._normalize_attributes(
                user_repr.get("attributes") or {}
            )
            incoming_attrs = self._normalize_attributes(attributes)
            current_attrs.update(incoming_attrs)

            user_repr["attributes"] = current_attrs
            self.admin.update_user(user_id, user_repr)
            logger.info(
                f"Атрибуты пользователя {user_id} обновлены: {list(current_attrs.keys())}"
            )
            return True
        except Exception as e:
            logger.error(f"Ошибка обновления атрибутов пользователя {user_id}: {e}")
            return False

    def custom_attributes_allowed(self) -> bool:
        """Проверяет, сохранит ли Keycloak незадекларированные атрибуты.

        Только чтение: смотрим unmanagedAttributePolicy в профиле реалма
        (user profile). Незадекларированные атрибуты сохраняются только при
        unmanagedAttributePolicy=ENABLED; в остальных случаях Keycloak их
        молча отбрасывает — сохранять нельзя.
        """
        self.check_token()
        try:
            profile = self.admin.get_realm_users_profile()
            return profile.get("unmanagedAttributePolicy") == "ENABLED"
        except Exception as e:
            logger.error(
                "Не удалось прочитать профиль пользователей реалма "
                f"{self._conn.realm}: {e}"
            )
            return False
