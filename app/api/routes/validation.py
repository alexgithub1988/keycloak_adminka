"""API роуты для управления правилами валидации."""

import csv
import io
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.infrastructure.keycloak_adapter import KeycloakAdminAdapter
from app.infrastructure.keycloak_admin.validation_service import (
    ValidationService,
)
from app.infrastructure.models import SessionLocal

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent.parent / "templates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _make_service(realm: str, db: Session) -> ValidationService:
    return ValidationService(db=db, realm=realm)


def _make_adapter(realm: str) -> KeycloakAdminAdapter:
    return KeycloakAdminAdapter(realm)


# ================================================================
# Страница управления правилами
# ================================================================


@router.get("/admin/validation")
def validation_page(request: Request, db: Session = Depends(get_db)):
    """Шаблон страницы управления правилами валидации."""
    realm = request.query_params.get("realm", "master")
    service = _make_service(realm, db)
    rules = service.get_rules()
    return templates.TemplateResponse(
        request,
        "validation.html",
        {"realm": realm, "rules": rules},
    )


# ================================================================
# CRUD правил
# ================================================================


@router.get("/api/validation/rules")
def api_get_rules(
    realm: str = "master",
    db: Session = Depends(get_db),
):
    """Получить список правил валидации для реалма."""
    service = _make_service(realm, db)
    rules = service.get_rules()
    return {
        "rules": [
            {
                "rule_type": r.rule_type,
                "rule_name": r.rule_name,
                "is_required": r.is_required,
                "description": r.description,
            }
            for r in rules
        ]
    }


@router.post("/api/validation/rules")
def api_set_rules(
    rules_json: str = Form(...),
    realm: str = "master",
    db: Session = Depends(get_db),
):
    """Установить правила валидации для реалма."""
    import json

    try:
        rules = json.loads(rules_json)
    except Exception:
        return {"ok": False, "error": "Invalid JSON"}

    service = _make_service(realm, db)
    created = service.set_rules(rules)
    return {"ok": True, "created": created}


@router.delete("/api/validation/rules")
def api_delete_rules(
    rule_type: str | None = Form(None),
    realm: str = "master",
    db: Session = Depends(get_db),
):
    """Удалить правила (все или по типу)."""
    service = _make_service(realm, db)
    service.delete_rules(rule_type)
    return {"ok": True}


# ================================================================
# Валидация CSV
# ================================================================


@router.post("/api/validation/validate-csv")
def api_validate_csv(
    file: str = Form(...),  # content of file as text
    realm: str = "master",
    db: Session = Depends(get_db),
):
    """Валидирует CSV-данные по правилам реалма."""
    try:
        reader = csv.DictReader(io.StringIO(file))
        rows = list(reader)
    except Exception as e:
        return {"ok": False, "error": f"CSV parse error: {e}"}

    service = _make_service(realm, db)
    adapter = _make_adapter(realm)
    report = service.validate_csv(rows, adapter)

    violations = []
    for v in report.violations:
        violations.append(
            {
                "row": v.row,
                "email": v.email,
                "missing_required": v.missing_required,
                "unknown_fields": v.unknown_fields,
                "missing_groups": v.missing_groups,
            }
        )

    return {
        "ok": True,
        "report": {
            "total_rows": report.total_rows,
            "valid_rows": report.valid_rows,
            "invalid_rows": report.invalid_rows,
            "stats": report.stats,
            "violations": violations,
        },
    }


# ================================================================
# Валидация существующих пользователей
# ================================================================


@router.get("/api/validation/validate-existing")
def api_validate_existing(
    realm: str = "master",
    db: Session = Depends(get_db),
):
    """Валидирует существующих пользователей в Keycloak по правилам."""
    service = _make_service(realm, db)
    adapter = _make_adapter(realm)
    report = service.validate_existing_users(adapter)

    violations = []
    for v in report.violations:
        violations.append(
            {
                "row": v.row,
                "email": v.email,
                "missing_required": v.missing_required,
                "missing_groups": v.missing_groups,
            }
        )

    return {
        "ok": True,
        "report": {
            "total_rows": report.total_rows,
            "valid_rows": report.valid_rows,
            "invalid_rows": report.invalid_rows,
            "stats": report.stats,
            "violations": violations,
        },
    }
