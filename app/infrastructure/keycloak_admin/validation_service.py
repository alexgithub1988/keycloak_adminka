"""Сервис валидации данных Keycloak по правилам для реалма.

Правила хранятся исключительно в БД через SQLAlchemy.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.infrastructure.keycloak_adapter import KeycloakAdminAdapter
from app.infrastructure.keycloak_admin.group_repository import GroupRepository
from app.infrastructure.models.validation_rule import RealmValidationRule

logger = logging.getLogger(__name__)


@dataclass
class Rule:
    """Правило валидации."""

    rule_type: str
    rule_name: str
    is_required: bool
    description: str = ""
    field_type: str = ""


@dataclass
class RowViolation:
    """Нарушение для одной строки."""

    row: int
    email: str
    missing_required: list[str] = field(default_factory=list)
    empty_optional: list[str] = field(default_factory=list)
    unknown_fields: list[str] = field(default_factory=list)
    missing_groups: list[str] = field(default_factory=list)
    unknown_groups: list[str] = field(default_factory=list)
    invalid_types: list[str] = field(default_factory=list)


@dataclass
class ValidationReport:
    """Отчёт валидации."""

    total_rows: int = 0
    valid_rows: int = 0
    invalid_rows: int = 0
    violations: list[RowViolation] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)


class ValidationService:
    """Сервис валидации CSV и существующих пользователей по правилам реалма."""

    def __init__(self, db: Session, realm: str):
        self.db = db
        self.realm = realm

    @staticmethod
    def _check_type(value: str, field_type: str) -> bool:
        """Проверяет, что строковое значение соответствует ожидаемому типу поля."""
        t = (field_type or "string").strip().lower()
        if t == "string":
            return True
        if t == "integer":
            try:
                int(value)
                return True
            except ValueError:
                return False
        if t == "boolean":
            return value.lower() in {
                "true",
                "false",
                "1",
                "0",
                "yes",
                "no",
                "y",
                "n",
                "t",
                "f",
            }
        return True  # неизвестный тип — не блокируем

    @staticmethod
    def _group_ref_matches(rule_name: str, ref: str) -> bool:
        """Проверяет, что ссылка на группу (имя или путь) соответствует правилу.

        rule_name — имя группы из правила (например, «Basic» или «/Basic»).
        ref — имя группы или её путь (например, «Basic» или «/Dept/Basic»).
        """
        rule = (rule_name or "").strip()
        ref = (ref or "").strip()
        if not rule or not ref:
            return False
        if rule.startswith("/"):
            return ref == rule
        if ref == rule:
            return True
        if ref.startswith("/"):
            return ref == f"/{rule}" or ref.endswith(f"/{rule}")
        return False

    # ================================================================
    # CRUD правил (только БД, через SQLAlchemy)
    # ================================================================

    def get_rules(self) -> list[Rule]:
        """Загружает все правила для текущего реалма из БД."""
        return self._get_rules_from_db()

    def set_rules(self, rules: list[dict]) -> list[str]:
        """Создаёт/обновляет правила в БД."""
        self._save_rules_to_db(rules)
        return [r.get("rule_name", "") for r in rules if r.get("rule_name")]

    def delete_rules(
        self,
        rule_type: str | None = None,
        rule_name: str | None = None,
    ) -> None:
        """Удаляет правила из БД: по имени, по типу или всё сразу."""
        self._delete_rules_from_db(rule_type, rule_name)

    # ================================================================
    # Валидация CSV
    # ================================================================

    def validate_csv(self, csv_data: list[dict], realm_admin) -> ValidationReport:
        rules = self.get_rules()
        if not rules:
            return ValidationReport(
                total_rows=len(csv_data), valid_rows=len(csv_data), invalid_rows=0
            )

        attr_rules = {r.rule_name: r for r in rules if r.rule_type == "attribute"}
        group_rules = {r.rule_name: r for r in rules if r.rule_type == "group"}
        required_attrs = {n for n, r in attr_rules.items() if r.is_required}
        required_groups = {n for n, r in group_rules.items() if r.is_required}
        attr_field_types = {
            n: r.field_type for n, r in attr_rules.items() if r.field_type
        }

        report = ValidationReport(total_rows=len(csv_data))

        # Полный список групп реалма — для проверки существования групп из CSV.
        flat_groups: list[dict] = []
        if realm_admin is not None and hasattr(realm_admin, "get_groups"):
            try:
                flat_groups = realm_admin.get_groups()
            except Exception as e:
                logger.warning(f"Не удалось получить группы для валидации: {e}")

        known_fields = set(attr_rules.keys()) | {
            "groups",
            "email",
            "username",
            "firstName",
            "lastName",
            "firstname",
            "lastname",
            "enabled",
            "emailVerified",
        }

        for idx, row in enumerate(csv_data, start=1):
            email = row.get("email") or row.get("username", "")
            violation = RowViolation(row=idx, email=email)

            for attr_name in required_attrs:
                if not str(row.get(attr_name, "") or "").strip():
                    violation.missing_required.append(attr_name)

            for key in row:
                if key not in known_fields and str(row[key] or "").strip():
                    violation.unknown_fields.append(key)

            for attr_name, ftype in attr_field_types.items():
                raw = str(row.get(attr_name, "") or "").strip()
                if raw and not self._check_type(raw, ftype):
                    violation.invalid_types.append(f"{attr_name} (ожидается {ftype})")

            # Группы: проверяем существование указанных в CSV и наличие обязательных.
            groups_val = str(row.get("groups", "") or "").strip()
            resolved_group_refs: set[str] = set()
            if groups_val:
                for ref in groups_val.split(";"):
                    ref = ref.strip()
                    if not ref:
                        continue
                    group = GroupRepository.resolve_group(ref, flat_groups)
                    if group is None:
                        violation.unknown_groups.append(ref)
                    else:
                        resolved_group_refs.add(group.get("name", ""))
                        resolved_group_refs.add(group.get("path", ""))

            for grp in required_groups:
                if not any(
                    self._group_ref_matches(grp, ref) for ref in resolved_group_refs
                ):
                    violation.missing_groups.append(grp)

            if (
                violation.missing_required
                or violation.unknown_fields
                or violation.missing_groups
                or violation.unknown_groups
                or violation.invalid_types
            ):
                report.invalid_rows += 1
                report.violations.append(violation)
            else:
                report.valid_rows += 1

        report.stats = {
            "total_rows": report.total_rows,
            "valid_rows": report.valid_rows,
            "invalid_rows": report.invalid_rows,
            "missing_required_fields": sorted(required_attrs),
            "missing_group_fields": sorted(required_groups),
            "unknown_fields": sorted(
                {f for v in report.violations for f in v.unknown_fields}
            ),
        }
        return report

    # ================================================================
    # Валидация существующих пользователей
    # ================================================================

    def validate_existing_users(self, realm_admin) -> ValidationReport:
        """Проверяет существующих пользователей в Keycloak по правилам."""
        rules = self.get_rules()
        if not rules:
            return ValidationReport()

        attr_rules = {r.rule_name: r for r in rules if r.rule_type == "attribute"}
        group_rules = {r.rule_name: r for r in rules if r.rule_type == "group"}
        required_attrs = {n for n, r in attr_rules.items() if r.is_required}
        required_groups = {n for n, r in group_rules.items() if r.is_required}
        attr_field_types = {
            n: r.field_type for n, r in attr_rules.items() if r.field_type
        }

        users = self._fetch_users_with_attributes()
        if not users:
            return ValidationReport(total_rows=0)

        report = ValidationReport(total_rows=len(users))
        for user in users:
            email = user.get("email", user.get("username", ""))
            violation = RowViolation(row=0, email=email)

            for attr_name in required_attrs:
                if not str(user.get(attr_name, "") or "").strip():
                    violation.missing_required.append(attr_name)

            for attr_name, ftype in attr_field_types.items():
                raw = str(user.get(attr_name, "") or "").strip()
                if raw and not self._check_type(raw, ftype):
                    violation.invalid_types.append(f"{attr_name} (ожидается {ftype})")

            user_group_refs = {
                g.strip()
                for g in str(user.get("groups", "") or "").split(";")
                if g.strip()
            }
            for grp in required_groups:
                if not any(
                    self._group_ref_matches(grp, ref) for ref in user_group_refs
                ):
                    violation.missing_groups.append(grp)

            if (
                violation.missing_required
                or violation.missing_groups
                or violation.invalid_types
            ):
                report.invalid_rows += 1
                report.violations.append(violation)
            else:
                report.valid_rows += 1

        report.stats = {
            "total_users": report.total_rows,
            "valid_users": report.valid_rows,
            "invalid_users": report.invalid_rows,
            "missing_required_attrs": sorted(required_attrs),
            "missing_required_groups": sorted(required_groups),
        }
        return report

    # ================================================================
    # Утилиты — fetch users
    # ================================================================

    def _fetch_users_with_attributes(self) -> list[dict]:
        # get_users_with_groups() возвращает пользователей с полем 'groups'
        # (пути групп через ';') и раскладывает атрибуты на верхний уровень.
        # Без этого поле 'groups' всегда пустое, и валидация обязательных
        # групп ложно помечала всех пользователей как «без группы».
        adapter = KeycloakAdminAdapter(self.realm)
        return adapter.get_users_with_groups()

    # ================================================================
    # БД CRUD
    # ================================================================

    def _get_rules_from_db(self) -> list[Rule]:
        rows = (
            self.db.query(RealmValidationRule)
            .filter(RealmValidationRule.realm == self.realm)
            .order_by(RealmValidationRule.rule_type, RealmValidationRule.rule_name)
            .all()
        )
        if not rows:
            return []
        return [
            Rule(
                rule_type=r.rule_type,
                rule_name=r.rule_name,
                is_required=r.is_required,
                description=r.description or "",
                field_type=r.field_type or "",
            )
            for r in rows
        ]

    def _save_rules_to_db(self, rules: list[dict]) -> None:
        """Добавляет новые правила или обновляет существующие (upsert),
        не затрагивая остальные правила реалма. Одному реалму может
        принадлежать сколь угодно много атрибутов и групп одновременно.
        """
        for r in rules:
            rule_type = r.get("rule_type", "")
            rule_name = r.get("rule_name", "").strip()
            if not rule_name:
                continue

            existing = (
                self.db.query(RealmValidationRule)
                .filter(
                    RealmValidationRule.realm == self.realm,
                    RealmValidationRule.rule_type == rule_type,
                    RealmValidationRule.rule_name == rule_name,
                )
                .first()
            )
            if existing:
                existing.is_required = bool(r.get("is_required", False))
                existing.description = r.get("description", "")
                existing.field_type = r.get("field_type", "") or ""
            else:
                self.db.add(
                    RealmValidationRule(
                        realm=self.realm,
                        rule_type=rule_type,
                        rule_name=rule_name,
                        is_required=bool(r.get("is_required", False)),
                        description=r.get("description", ""),
                        field_type=r.get("field_type", "") or "",
                    )
                )
        self.db.commit()

    def _delete_rules_from_db(
        self,
        rule_type: str | None,
        rule_name: str | None,
    ) -> None:
        q = self.db.query(RealmValidationRule).filter(
            RealmValidationRule.realm == self.realm
        )
        if rule_name:
            q = q.filter(RealmValidationRule.rule_name == rule_name)
        if rule_type:
            q = q.filter(RealmValidationRule.rule_type == rule_type)
        q.delete(synchronize_session="fetch")
        self.db.commit()
