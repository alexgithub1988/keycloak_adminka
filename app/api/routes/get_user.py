from fastapi import APIRouter

from app.infrastructure.keycloack_adapter import KeycloakAdminAdapter

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/")
def get_users():
    admin = KeycloakAdminAdapter("master")
    return admin.get_users()
