import logging

from fastapi import APIRouter

from app.infrastructure.keycloak_adapter import KeycloakAdminAdapter

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/api/realm/list")
def get_realm_list():
    """Возвращает список доступных реалмов из Keycloak."""
    try:
        # realm=master, т.к. get_realms() вызывается в master
        adapter = KeycloakAdminAdapter("master")
        realms = adapter.get_realms_list()
        return {"realms": realms}
    except Exception as e:
        logger.error(f"Ошибка получения списка реалмов: {e}")
        return {"realms": []}
