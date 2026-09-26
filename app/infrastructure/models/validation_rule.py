from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from app.infrastructure.models import Base


class RealmValidationRule(Base):
    __tablename__ = "realm_validation_rule"

    id = Column(Integer, primary_key=True, index=True)
    realm = Column(String(100), nullable=False, index=True)
    rule_type = Column(String(20), nullable=False)  # "attribute" | "group"
    rule_name = Column(String(255), nullable=False)
    is_required = Column(Boolean, default=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("realm", "rule_type", "rule_name", name="uq_realm_rule"),
    )

    def __repr__(self):
        return (
            f"<RealmValidationRule(id={self.id}, realm='{self.realm}', "
            f"type='{self.rule_type}', name='{self.rule_name}', "
            f"required={self.is_required})>"
        )
