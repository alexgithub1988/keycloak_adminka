from fastapi import APIRouter
from app.infrastructure.keycloack_adapter import KeycloakAdminAdapter



router = APIRouter()

def get_adapter(username,password,realm)
    """Get adapter"""
    admin_user = KeycloakAdminAdapter(username,password,realm)
    return admin_user