"""API роуты для управления правилами валидации."""

import csv
import io
import logging
from pathlib import Path

from fastapi import APIRouter, Body, Depends, Form, Query, Request
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
    response = templates.TemplateResponse(
        request,
        "validation.html",
        {"realm": realm, "rules": rules},
    )
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# ================================================================
# CRUD правил
# ================================================================


@router.get("/api/validation/rules")
def api_get_rules(
    realm: str = Query("master"),
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
    data: dict = Body(...),
    realm: str = Query("master"),
    db: Session = Depends(get_db),
):
    """Установить правила валидации для реалма."""
    import json

    # Поддерживаем разные форматы body
    rules = None

    # Если прислали JSON с rules_json
    if "rules_json" in data:
        rules_str = data["rules_json"]
        if isinstance(rules_str, str):
            try:
                rules = json.loads(rules_str)
            except Exception:
                return {"ok": False, "error": "Invalid JSON in rules_json"}
        elif isinstance(rules_str, list):
            rules = rules_str
    # Если прислали JSON с rules
    elif "rules" in data and isinstance(data["rules"], list):
        rules = data["rules"]
    # Если Form data с rules_json
    elif "rules_json" in data:
        try:
            rules = json.loads(data["rules_json"])
        except Exception:
            return {"ok": False, "error": "Invalid JSON in rules_json"}

    if not rules or not isinstance(rules, list):
        return {"ok": False, "error": "No valid rules provided"}

    service = _make_service(realm, db)
    created = service.set_rules(rules)
    return {"ok": True, "created": created}


@router.delete("/api/validation/rules")
def api_delete_rules(
    rule_type: str | None = Query(None),
    realm: str = Query("master"),
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
    realm: str = Query("master"),
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
    realm: str = Query("master"),
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
