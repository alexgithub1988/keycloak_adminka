"""Сервис валидации данных Keycloak по правилам для реалма.

Гибридный подход: приоритет у БД, fallback на JSON-файл.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

CONFIGS_DIR = Path(__file__).parent.parent.parent.parent / "configs" / "realm_rules"
CONFIGS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class Rule:
    """Правило валидации."""

    rule_type: str
    rule_name: str
    is_required: bool
    description: str = ""


@dataclass
class RowViolation:
    """Нарушение для одной строки."""

    row: int
    email: str
    missing_required: list[str] = field(default_factory=list)
    empty_optional: list[str] = field(default_factory=list)
    unknown_fields: list[str] = field(default_factory=list)
    missing_groups: list[str] = field(default_factory=list)


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

    # ================================================================
    # CRUD правил (БД + JSON fallback)
    # ================================================================

    def get_rules(self) -> list[Rule]:
        """Загружает все правила для текущего реалма (БД → JSON)."""
        db_rules = self._get_rules_from_db()
        if db_rules:
            return db_rules
        return self._get_rules_from_json()

    def set_rules(self, rules: list[dict]) -> list[str]:
        """Создаёт/обновляет правила (сохраняет и в БД, и в JSON)."""
        self._save_rules_to_db(rules)
        self._save_rules_to_json(rules)
        return [r.get("rule_name", "") for r in rules if r.get("rule_name")]

    def delete_rules(self, rule_type: str | None = None) -> None:
        """Удаляет правила (и из БД, и из JSON)."""
        self._delete_rules_from_db(rule_type)
        self._delete_rules_from_json(rule_type)

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

        report = ValidationReport(total_rows=len(csv_data))
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

            if required_groups:
                groups_val = str(row.get("groups", "") or "").strip()
                for grp in required_groups:
                    if not groups_val or grp not in groups_val:
                        violation.missing_groups.append(grp)

            if (
                violation.missing_required
                or violation.unknown_fields
                or violation.missing_groups
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

            user_groups = str(user.get("groups", "") or "")
            for grp in required_groups:
                if not user_groups or grp not in user_groups:
                    violation.missing_groups.append(grp)

            if violation.missing_required or violation.missing_groups:
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
        from app.infrastructure.keycloak_adapter import KeycloakAdminAdapter

        adapter = KeycloakAdminAdapter(self.realm)
        users = adapter.get_users()
        result = []
        for user in users:
            attrs = user.pop("attributes", {})
            for k, v in attrs.items():
                if isinstance(v, list):
                    user[k] = v[0] if v else ""
                else:
                    user[k] = v or ""
            result.append(user)
        return result

    # ================================================================
    # БД CRUD
    # ================================================================

    def _get_rules_from_db(self) -> list[Rule]:
        from app.infrastructure.models.validation_rule import (
            RealmValidationRule as Model,
        )

        rows = (
            self.db.query(Model)
            .filter(Model.realm == self.realm)
            .order_by(Model.rule_type, Model.rule_name)
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
            )
            for r in rows
        ]

    def _save_rules_to_db(self, rules: list[dict]) -> None:
        from app.infrastructure.models.validation_rule import (
            RealmValidationRule as Model,
        )

        self.db.query(Model).filter(Model.realm == self.realm).delete()
        for r in rules:
            self.db.add(
                Model(
                    realm=self.realm,
                    rule_type=r.get("rule_type", ""),
                    rule_name=r.get("rule_name", "").strip(),
                    is_required=bool(r.get("is_required", False)),
                    description=r.get("description", ""),
                )
            )
        self.db.commit()

    def _delete_rules_from_db(self, rule_type: str | None) -> None:
        from app.infrastructure.models.validation_rule import (
            RealmValidationRule as Model,
        )

        q = self.db.query(Model).filter(Model.realm == self.realm)
        if rule_type:
            q = q.filter(Model.rule_type == rule_type)
        q.delete(synchronize_session="fetch")
        self.db.commit()

    # ================================================================
    # JSON CRUD
    # ================================================================

    def _get_rules_from_json(self) -> list[Rule]:
        config_path = CONFIGS_DIR / f"{self.realm}.json"
        if not config_path.exists():
            return []
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            rules = data.get("rules", [])
            return [
                Rule(
                    rule_type=r.get("rule_type", ""),
                    rule_name=r.get("rule_name", "").strip(),
                    is_required=bool(r.get("is_required", False)),
                    description=r.get("description", ""),
                )
                for r in rules
                if r.get("rule_name")
            ]
        except Exception as e:
            logger.error(f"Ошибка чтения JSON config {config_path}: {e}")
            return []

    def _save_rules_to_json(self, rules: list[dict]) -> None:
        config_path = CONFIGS_DIR / f"{self.realm}.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        data = {"realm": self.realm, "rules": rules}
        config_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _delete_rules_from_json(self, rule_type: str | None) -> None:
        config_path = CONFIGS_DIR / f"{self.realm}.json"
        if not config_path.exists():
            return
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            if rule_type:
                data["rules"] = [
                    r for r in data.get("rules", []) if r.get("rule_type") != rule_type
                ]
            else:
                data["rules"] = []
            config_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error(f"Ошибка удаления JSON config {config_path}: {e}")
