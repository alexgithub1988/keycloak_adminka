from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.infrastructure.models import Base


class AuditRecord(Base):
    __tablename__ = "audit"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    action = Column(
        String(100), nullable=False
    )  # UPLOAD_FILE, VIEW_USERS, DOWNLOAD_FILE, etc.
    user_email = Column(String(255))  # Email пользователя
    file_name = Column(String(255))  # Имя файла (если применимо)
    file_path = Column(String(500))  # Путь к файлу в файловой системе
    summary = Column(Text)  # Резюме операции (например, сколько пользователей создано)
    realm = Column(String(100))  # Realm в Keycloak
    ip_address = Column(String(45))  # IP адрес пользователя
    result = Column(String(50))  # SUCCESS, FAILED, PARTIAL_SUCCESS, etc.

    def __repr__(self):
        return f"<AuditRecord(id={self.id}, action='{self.action}', user='{self.user_email}', timestamp='{self.timestamp}')>"
