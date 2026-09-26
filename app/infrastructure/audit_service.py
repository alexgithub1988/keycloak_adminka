import os
from datetime import datetime
from typing import List, Optional

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from app.infrastructure.models.audit import AuditRecord


class AuditService:
    """Сервис для работы с аудит-логами"""

    @staticmethod
    def create_record(
        db: Session,
        action: str,
        user_email: Optional[str] = None,
        file_name: Optional[str] = None,
        file_content: Optional[str] = None,  # Optional - for saving to file system
        summary: Optional[str] = None,
        realm: Optional[str] = None,
        ip_address: Optional[str] = None,
        result: Optional[str] = None,
    ) -> AuditRecord:
        """
        Создает новую запись аудита

        Args:
            db: Сессия SQLAlchemy
            action: Действие (UPLOAD_FILE, VIEW_USERS, DOWNLOAD_FILE и т.д.)
            user_email: Email пользователя
            file_name: Имя файла
            file_content: Содержимое файла (если нужно сохранить в файловую систему)
            summary: Резюме операции
            realm: Realm в Keycloak
            ip_address: IP адрес пользователя
            result: Результат операции (SUCCESS, FAILED, PARTIAL_SUCCESS)

        Returns:
            AuditRecord: Созданная запись аудита
        """
        # Prepare file storage
        file_path = None
        if file_content and file_name:
            # Create uploads directory if it doesn't exist
            uploads_dir = "/home/alex/keycloak_adminka/uploads"
            os.makedirs(uploads_dir, exist_ok=True)

            # Generate unique filename to avoid conflicts
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            base_name, ext = os.path.splitext(file_name)
            unique_filename = f"{base_name}_{timestamp}{ext}"
            file_path = os.path.join(uploads_dir, unique_filename)

            # Save file to filesystem
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(file_content)
            except Exception as e:
                print(f"Error saving file {file_path}: {e}")
                file_path = None

        audit_record = AuditRecord(
            timestamp=datetime.utcnow(),
            action=action,
            user_email=user_email,
            file_name=file_name,
            file_path=file_path,  # Store file path instead of content
            summary=summary,
            realm=realm,
            ip_address=ip_address,
            result=result,
        )

        db.add(audit_record)
        db.commit()
        db.refresh(audit_record)

        return audit_record

    @staticmethod
    def get_history(db: Session, limit: int = 100) -> List[AuditRecord]:
        """
        Получает последние N записей аудита

        Args:
            db: Сессия SQLAlchemy
            limit: Количество записей для получения

        Returns:
            List[AuditRecord]: Список записей аудита
        """
        return (
            db.query(AuditRecord)
            .order_by(desc(AuditRecord.timestamp))
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_record_by_id(db: Session, record_id: int) -> Optional[AuditRecord]:
        """
        Получает конкретную запись аудита по ID

        Args:
            db: Сессия SQLAlchemy
            record_id: ID записи

        Returns:
            Optional[AuditRecord]: Запись аудита или None
        """
        return db.query(AuditRecord).filter(AuditRecord.id == record_id).first()

    @staticmethod
    def get_records_by_user(
        db: Session, user_email: str, limit: int = 100
    ) -> List[AuditRecord]:
        """
        Получает записи аудита по пользователю

        Args:
            db: Сессия SQLAlchemy
            user_email: Email пользователя
            limit: Количество записей для получения

        Returns:
            List[AuditRecord]: Список записей аудита
        """
        return (
            db.query(AuditRecord)
            .filter(AuditRecord.user_email == user_email)
            .order_by(desc(AuditRecord.timestamp))
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_records_by_file(db: Session, file_name: str) -> List[AuditRecord]:
        """
        Получает записи аудита по имени файла

        Args:
            db: Сессия SQLAlchemy
            file_name: Имя файла

        Returns:
            List[AuditRecord]: Список записей аудита
        """
        return (
            db.query(AuditRecord)
            .filter(AuditRecord.file_name == file_name)
            .order_by(desc(AuditRecord.timestamp))
            .all()
        )

    @staticmethod
    def get_records_by_action(
        db: Session, action: str, limit: int = 100
    ) -> List[AuditRecord]:
        """
        Получает записи аудита по типу действия

        Args:
            db: Сессия SQLAlchemy
            action: Тип действия
            limit: Количество записей для получения

        Returns:
            List[AuditRecord]: Список записей аудита
        """
        return (
            db.query(AuditRecord)
            .filter(AuditRecord.action == action)
            .order_by(desc(AuditRecord.timestamp))
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_records_by_date_range(
        db: Session, start_date: datetime, end_date: datetime, limit: int = 100
    ) -> List[AuditRecord]:
        """
        Получает записи аудита за определенный период

        Args:
            db: Сессия SQLAlchemy
            start_date: Начальная дата
            end_date: Конечная дата
            limit: Количество записей для получения

        Returns:
            List[AuditRecord]: Список записей аудита
        """
        return (
            db.query(AuditRecord)
            .filter(
                and_(
                    AuditRecord.timestamp >= start_date,
                    AuditRecord.timestamp <= end_date,
                )
            )
            .order_by(desc(AuditRecord.timestamp))
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_file_content(file_path: str) -> Optional[str]:
        """
        Получает содержимое файла из файловой системы

        Args:
            file_path: Путь к файлу

        Returns:
            Optional[str]: Содержимое файла или None если файл не найден
        """
        if not file_path or not os.path.exists(file_path):
            return None

        try:
            with open(file_path, encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return None

    @staticmethod
    def delete_record(db: Session, record_id: int) -> bool:
        """
        Удаляет запись аудита и связанный файл

        Args:
            db: Сессия SQLAlchemy
            record_id: ID записи для удаления

        Returns:
            bool: True если запись была удалена, иначе False
        """
        record = db.query(AuditRecord).filter(AuditRecord.id == record_id).first()
        if record:
            # Delete associated file if it exists
            if record.file_path and os.path.exists(record.file_path):
                try:
                    os.remove(record.file_path)
                except Exception as e:
                    print(f"Error deleting file {record.file_path}: {e}")

            db.delete(record)
            db.commit()
            return True
        return False
