import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.infrastructure.models import Base
from app.infrastructure.models.audit import AuditRecord  # noqa: F401
from app.infrastructure.models.validation_rule import RealmValidationRule


@pytest.fixture()
def db_session():
    """Отдельная база в памяти не связанная с основной"""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)

    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def make_rule(db_session):
    """Создаем фабрику правила и комитим в базу"""

    def _make(
        rule_type,
        rule_name,
        realm="test",
        is_required=False,
        description=None,
        field_type="string",
    ):
        rule = RealmValidationRule(
            rule_type=rule_type,
            rule_name=rule_name,
            realm=realm,
            is_required=is_required,
            description=description,
            field_type=field_type,
        )
        db_session.add(rule)
        db_session.commit()
        return rule

    return _make
