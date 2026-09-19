from fastapi import APIRouter, Request

from app.infrastructure.keycloak_adapter import KeycloakAdminAdapter

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/")
async def get_users(request: Request):
    realm = request.query_params.get("realm", "master")
    admin = KeycloakAdminAdapter(realm)
    return admin.get_users()
