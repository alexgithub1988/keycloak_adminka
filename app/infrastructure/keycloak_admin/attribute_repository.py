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

    def set_user_attributes(self, user_id: str, attributes: dict) -> bool:
        """Устанавливает атрибуты пользователя (region_code, municipality_id и т.д.)."""
        self.check_token()
        try:
            formatted_attrs = {k: [v] for k, v in attributes.items() if v}
            if formatted_attrs:
                self.admin.set_user_attributes(user_id, formatted_attrs)
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
            current_attrs = self.admin.get_user_attributes(user_id)
            if current_attrs is None:
                current_attrs = {}

            for k, v in attributes.items():
                if v:
                    current_attrs[k] = str(v)

            formatted_attrs = {k: [v] for k, v in current_attrs.items()}
            if formatted_attrs:
                self.admin.set_user_attributes(user_id, formatted_attrs)
                logger.info(
                    f"Атрибуты пользователя {user_id} обновлены: {list(formatted_attrs.keys())}"
                )
            return True
        except Exception as e:
            logger.error(f"Ошибка обновления атрибутов пользователя {user_id}: {e}")
            return False
