from fastapi import APIRouter, Request

from app.infrastructure.keycloak_adapter import KeycloakAdminAdapter

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/")
def get_users(request: Request):
    realm = request.query_params.get("realm", "master")
    admin = KeycloakAdminAdapter(realm)
    return admin.get_users()


@router.get("/count")
def count_users(request: Request):
    """Cчитаем количество пользователей в реалме"""
    users = get_users(request)
    count = len(users)
    return {"count": count}
