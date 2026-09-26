"""Управление группами пользователей в Keycloak."""

import logging

logger = logging.getLogger(__name__)


class GroupRepository:
    """Операции с группами: чтение дерева, членство пользователей."""

    def __init__(self, connection):
        self._conn = connection

    def check_token(self):
        self._conn.check_token()

    @property
    def admin(self):
        return self._conn.admin

    def get_groups(self) -> list:
        """Получает дерево групп реалма (полная иерархия)."""
        self.check_token()
        try:
            return self.admin.get_groups(full_hierarchy=True)
        except Exception as e:
            logger.error(f"Не удалось получить список групп: {e}")
            return []

    def get_user_groups(self, user_id: str) -> list:
        """Получает список групп пользователя."""
        self.check_token()
        try:
            return self.admin.get_user_groups(user_id)
        except Exception as e:
            logger.error(f"Не удалось получить группы пользователя {user_id}: {e}")
            return []

    def add_user_to_group(self, user_id: str, group_id: str) -> bool:
        """Добавляет пользователя в группу."""
        self.check_token()
        try:
            self.admin.group_user_add(user_id, group_id)
            logger.info(f"Пользователь {user_id} добавлен в группу {group_id}")
            return True
        except Exception as e:
            logger.error(
                f"Ошибка добавления пользователя {user_id} в группу {group_id}: {e}"
            )
            return False

    def remove_user_from_group(self, user_id: str, group_id: str) -> bool:
        """Удаляет пользователя из группы."""
        self.check_token()
        try:
            self.admin.group_user_remove(user_id, group_id)
            logger.info(f"Пользователь {user_id} удалён из группы {group_id}")
            return True
        except Exception as e:
            logger.error(
                f"Ошибка удаления пользователя {user_id} из группы {group_id}: {e}"
            )
            return False

    @staticmethod
    def flatten_groups(groups: list, parent_path: str = "") -> list[dict]:
        """Разворачивает дерево групп в плоский список {'id', 'name', 'path'}."""
        flat = []
        for group in groups:
            name = group.get("name", "")
            path = group.get("path") or f"{parent_path}/{name}"
            flat.append({"id": group.get("id"), "name": name, "path": path})

            sub_groups = group.get("subGroups") or []
            if sub_groups:
                flat.extend(
                    GroupRepository.flatten_groups(sub_groups, parent_path=path)
                )

        return flat

    @staticmethod
    def resolve_group(group_ref: str, flat_groups: list[dict]) -> dict | None:
        """
        Ищет группу среди уже существующих.
        Если group_ref начинается с '/' — ищет по полному пути.
        Иначе — по имени (должно быть найдено ровно одно совпадение).
        """
        group_ref = group_ref.strip()
        if not group_ref:
            return None

        if group_ref.startswith("/"):
            for group in flat_groups:
                if group["path"] == group_ref:
                    return group
            logger.warning(f"Группа с путём '{group_ref}' не найдена")
            return None

        matches = [g for g in flat_groups if g["name"] == group_ref]
        if len(matches) == 1:
            return matches[0]
        if len(matches) == 0:
            logger.warning(f"Группа с именем '{group_ref}' не найдена")
        else:
            logger.warning(
                f"Имя группы '{group_ref}' неоднозначно "
                f"(найдено {len(matches)} групп), используйте полный путь"
            )
        return None
