from typing import Dict, Optional, Tuple

from fastapi import Request


class MessageHandler:
    """Сервис для обработки сообщений и формирования данных для отображения"""

    @staticmethod
    def process_request_messages(
        request: Request,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Обрабатывает параметры запроса и возвращает данные для отображения сообщений

        Args:
            request: Объект запроса FastAPI

        Returns:
            Кортеж из (message_dict, stats_string) или (None, None) если нет сообщений
        """
        message = None
        stats = None

        if "success" in request.query_params:
            if request.query_params.get("success") == "upload_complete":
                created = request.query_params.get("created", "0")
                updated = request.query_params.get("updated", "0")
                skipped = request.query_params.get("skipped", "0")
                message = {
                    "type": "success",
                    "icon": "check-circle-fill",
                    "text": "Файл успешно загружен и пользователи созданы!",
                }
                stats = (
                    f"Создано: {created}, Обновлено: {updated}, Пропущено: {skipped}"
                )

        elif "warning" in request.query_params:
            if request.query_params.get("warning") == "partial_success":
                created = request.query_params.get("created", "0")
                updated = request.query_params.get("updated", "0")
                skipped = request.query_params.get("skipped", "0")
                message = {
                    "type": "warning",
                    "icon": "exclamation-triangle-fill",
                    "text": "Часть пользователей не создана/обновлена (возможно, ошибки). Проверьте логи.",
                }
                stats = (
                    f"Создано: {created}, Обновлено: {updated}, Пропущено: {skipped}"
                )

        elif "error" in request.query_params:
            if request.query_params.get("error") == "csv_only":
                message = {
                    "type": "danger",
                    "icon": "exclamation-triangle-fill",
                    "text": "Разрешены только CSV файлы!",
                }
            elif request.query_params.get("error") == "upload_failed":
                created = request.query_params.get("created", "0")
                skipped = request.query_params.get("skipped", "0")
                message = {
                    "type": "warning",
                    "icon": "exclamation-circle-fill",
                    "text": "Часть пользователей не была создана (возможно, дубликаты). Проверьте логи.",
                }
                stats = f"Создано: {created}, Пропущено: {skipped}"
            elif request.query_params.get("error") == "all_failed":
                message = {
                    "type": "danger",
                    "icon": "exclamation-triangle-fill",
                    "text": "Не удалось создать ни одного пользователя. Проверьте формат CSV.",
                }

        return message, stats
