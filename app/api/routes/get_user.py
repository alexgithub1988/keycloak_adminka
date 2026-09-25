from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.infrastructure.audit_service import AuditService
from app.infrastructure.keycloak_adapter import KeycloakAdminAdapter
from app.infrastructure.models import SessionLocal

router = APIRouter(prefix="/users", tags=["users"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/")
def get_users(request: Request, db: Session = Depends(get_db)):
    realm = request.query_params.get("realm", "master")
    user_email = request.session.get("user_email", "anonymous")
    client_ip = request.client.host

    admin = KeycloakAdminAdapter(realm)
    users = admin.get_users()

    # Записываем операцию просмотра пользователей в аудит
    AuditService.create_record(
        db=db,
        action="VIEW_USERS",
        user_email=user_email,
        realm=realm,
        ip_address=client_ip,
        result="SUCCESS",
        summary=f"Viewed {len(users)} users",
    )

    return users


@router.get("/count")
def count_users(request: Request, db: Session = Depends(get_db)):
    """Cчитаем количество пользователей в реалме"""
    realm = request.query_params.get("realm", "master")
    user_email = request.session.get("user_email", "anonymous")
    client_ip = request.client.host

    admin = KeycloakAdminAdapter(realm)
    users = admin.get_users()
    count = len(users)

    # Записываем операцию просмотра количества пользователей в аудит
    AuditService.create_record(
        db=db,
        action="VIEW_USERS_COUNT",
        user_email=user_email,
        realm=realm,
        ip_address=client_ip,
        result="SUCCESS",
        summary=f"Counted {count} users",
    )

    return {"count": count}
