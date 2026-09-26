"""Сервис для импорта пользователей из CSV (create_from_list, create_or_update_user)."""

import logging

logger = logging.getLogger(__name__)


class CsvImportService:
    """Импорт/обновление пользователей из списка словарей (CSV-формат)."""

    def __init__(
        self,
        user_repo,
        attr_repo,
        group_repo,
        basic_fields: list[str],
        attribute_fields: list[str],
    ):
        self._user_repo = user_repo
        self._attr_repo = attr_repo
        self._group_repo = group_repo
        self._basic_fields = set(basic_fields)
        self._attribute_fields = set(attribute_fields)

    # ---- внутренние хелперы ------------------------------------------------

    def _extract_user_key(self, row: dict) -> str:
        """Извлекает ключ поиска пользователя (email или username)."""
        return row.get("email") or row.get("username", "")

    def _separate_basic_and_attributes(self, row: dict) -> tuple[dict, dict]:
        """Разделяет row на basic fields и атрибуты на основе белых списков."""
        basic = {}
        attributes = {}
        for key, value in row.items():
            if key in self._basic_fields:
                basic[key] = value
            elif key in self._attribute_fields:
                attributes[key] = value
        return basic, attributes

    # ---- create_or_update_user --------------------------------------------

    def create_or_update_user(
        self, row: dict, flat_groups: list[dict] | None = None
    ) -> dict:
        """
        Создает или обновляет пользователя.

        Если в row есть поле 'groups' (разделитель ';') — добавляет пользователя
        в существующие группы Keycloak (не найденные группы пропускаются
        с предупреждением).

        Возвращает:
            {
                'action': 'created' | 'updated' | 'error',
                'details': str,
                'group_warnings': list[str],
            }
        """
        email = row.get("email", row.get("username", ""))
        username = row.get("username", email)
        enabled = row.get("enabled", True)
        firstname = row.get("firstname", row.get("firstName", ""))
        lastname = row.get("lastname", row.get("lastName", ""))
        groups_value = row.get("groups", "")

        _basic, attributes = self._separate_basic_and_attributes(row)

        if not email:
            return {
                "action": "error",
                "details": "Отсутствует email/username",
                "group_warnings": [],
            }

        try:
            existing_user = self._user_repo.find_user(
                email=email,
                username=username,
                firstname=firstname,
                lastname=lastname,
            )

            if existing_user:
                return self._update_existing(
                    existing_user=existing_user,
                    email=email,
                    username=username,
                    firstname=firstname,
                    lastname=lastname,
                    enabled=enabled,
                    attributes=attributes,
                    groups_value=groups_value,
                    flat_groups=flat_groups,
                )

            return self._create_new(
                email=email,
                username=username,
                firstname=firstname,
                lastname=lastname,
                enabled=enabled,
                attributes=attributes,
                groups_value=groups_value,
                flat_groups=flat_groups,
            )
        except Exception as e:
            logger.error(f"Ошибка обработки пользователя {email}: {e}", exc_info=True)
            return {
                "action": "error",
                "details": f"Ошибка обработки пользователя {email}: {str(e)}",
                "group_warnings": [],
            }

    # ---- create_from_list -------------------------------------------------

    def create_from_list(self, list_of_dicts: list) -> dict:
        """
        Создаёт или обновляет пользователей из списка словарей.

        Возвращает:
            {
                'created': int, 'updated': int, 'skipped': int,
                'errors': list[str], 'group_warnings': int,
            }
        """
        if not list_of_dicts:
            logger.warning("Получен пустой список для загрузки")
            return {
                "created": 0,
                "updated": 0,
                "skipped": 0,
                "errors": [],
                "group_warnings": 0,
            }

        first_row = list_of_dicts[0]
        keys = set(first_row.keys())

        created = 0
        updated = 0
        skipped = 0
        errors = []
        group_warnings = 0

        has_groups_column = "groups" in keys
        flat_groups = []
        if has_groups_column:
            try:
                groups = self._group_repo.get_groups()
                flat_groups = self._group_repo.flatten_groups(groups)
            except Exception as e:
                logger.error(
                    f"Не удалось получить группы для реалма {self._conn.realm}: {e}"
                )
                flat_groups = []

        if "email" in keys or "username" in keys:
            logger.info("Распознан формат CSV (email или username)")
            for row in list_of_dicts:
                user_key = self._extract_user_key(row)
                if not user_key:
                    logger.warning("Пропуск строки: отсутствует email/username")
                    skipped += 1
                    continue

                result = self.create_or_update_user(row, flat_groups=flat_groups)

                if result["action"] == "created":
                    created += 1
                    logger.info(f"Создан: {result['details']}")
                elif result["action"] == "updated":
                    updated += 1
                    logger.info(f"Обновлён: {result['details']}")
                else:
                    skipped += 1
                    errors.append(result["details"])
                    logger.warning(result["details"])

                for warning in result.get("group_warnings", []):
                    group_warnings += 1
                    errors.append(warning)
                    logger.warning(warning)
        else:
            logger.error(
                f"Неизвестный формат CSV. Ожидалось 'email' или 'username'. "
                f"Доступные поля в первом ряду: {list(first_row.keys())}"
            )
            return {
                "created": 0,
                "updated": 0,
                "skipped": 0,
                "errors": ["Неизвестный формат CSV"],
                "group_warnings": 0,
            }

        logger.info(
            f"Загрузка завершена: создано={created}, обновлено={updated}, "
            f"пропущено={skipped}, предупреждений по группам={group_warnings}, "
            f"всего строк={len(list_of_dicts)}"
        )
        return {
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "errors": errors,
            "group_warnings": group_warnings,
        }

    # ---- get_users_with_groups --------------------------------------------

    def get_users_with_groups(self) -> list:
        """
        Получает список пользователей вместе с группами.
        Каждому пользователю добавляется поле 'groups' — пути групп через ';'.
        А также раскладывает атрибуты на верхний уровень.
        """
        users = self._user_repo.get_users()
        if not users:
            return users or []

        flat_groups = self._group_repo.flatten_groups(self._group_repo.get_groups())
        group_by_id = {g["id"]: g for g in flat_groups}

        for user in users:
            try:
                user_groups = self._group_repo.get_user_groups(user["id"])
                paths = []
                for group in user_groups:
                    gid = group.get("id")
                    if gid in group_by_id:
                        paths.append(group_by_id[gid]["path"])
                    else:
                        paths.append(group.get("path") or group.get("name", ""))
                user["groups"] = ";".join(paths)
            except Exception as e:
                logger.error(
                    f"Не удалось получить группы пользователя " f"{user.get('id')}: {e}"
                )
                user["groups"] = ""

            # Раскладываем атрибуты на верхний уровень
            attributes = user.pop("attributes", {})
            if attributes:
                for attr_name, attr_values in attributes.items():
                    user[attr_name] = attr_values[0] if attr_values else ""

        return users

    # ---- приватные хелперы: ветки create / update --------------------------

    def _create_new(
        self,
        email: str,
        username: str,
        firstname: str,
        lastname: str,
        enabled: bool,
        attributes: dict,
        groups_value: str,
        flat_groups: list[dict] | None,
    ) -> dict:
        """Ветка создания нового пользователя."""
        try:
            result = self._user_repo.create_user(
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
                    "group_warnings": [],
                }

            user_id = result["id"]

            if attributes:
                self._attr_repo.set_user_attributes(
                    user_id=user_id, attributes=attributes
                )

            group_warnings = self._assign_user_groups(
                user_id=user_id,
                email=email,
                groups_value=groups_value,
                flat_groups=flat_groups or [],
            )

            return {
                "action": "created",
                "details": f"Пользователь {email} создан",
                "group_warnings": group_warnings,
            }
        except Exception as e:
            logger.error(
                f"Ошибка при создании пользователя {email}: {e}", exc_info=True
            )
            return {
                "action": "error",
                "details": f"Ошибка при создании пользователя {email}: {str(e)}",
                "group_warnings": [],
            }

    def _update_existing(
        self,
        existing_user: dict,
        email: str,
        username: str,
        firstname: str,
        lastname: str,
        enabled: bool,
        attributes: dict,
        groups_value: str,
        flat_groups: list[dict] | None,
    ) -> dict:
        """Ветка обновления существующего пользователя."""
        try:
            user_id = existing_user["id"]

            self._user_repo.update_user_basic_info(
                user_id=user_id,
                email=email,
                username=username,
                firstname=firstname,
                lastname=lastname,
                enabled=enabled,
            )

            if attributes:
                self._attr_repo.update_user_attributes(
                    user_id=user_id, attributes=attributes
                )

            group_warnings: list[str] = []
            if groups_value and flat_groups:
                group_warnings = self._assign_user_groups(
                    user_id=user_id,
                    email=email,
                    groups_value=groups_value,
                    flat_groups=flat_groups,
                )

            return {
                "action": "updated",
                "details": f"Пользователь {email} обновлён",
                "group_warnings": group_warnings,
            }
        except Exception as e:
            logger.error(
                f"Ошибка при обновлении пользователя {email}: {e}", exc_info=True
            )
            return {
                "action": "error",
                "details": f"Ошибка при обновлении пользователя {email}: {str(e)}",
                "group_warnings": [],
            }

    def _assign_user_groups(
        self,
        user_id: str,
        email: str,
        groups_value: str,
        flat_groups: list[dict],
    ) -> list[str]:
        """Добавляет пользователя в группы, указанные в CSV (разделитель ';')."""
        warnings: list[str] = []
        if not groups_value:
            return warnings

        group_refs = [g.strip() for g in str(groups_value).split(";") if g.strip()]
        for ref in group_refs:
            try:
                group = self._group_repo.resolve_group(ref, flat_groups)
                if group is None:
                    warnings.append(
                        f"Пользователь {email}: группа '{ref}' не найдена, пропущена"
                    )
                    continue
                self._group_repo.add_user_to_group(user_id, group["id"])
            except Exception as e:
                logger.error(
                    f"Ошибка при добавлении пользователя {email} в группу '{ref}': {e}"
                )
                warnings.append(
                    f"Пользователь {email}: ошибка при добавлении в группу '{ref}': {str(e)}"
                )

        return warnings
