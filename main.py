import logging
import os

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.api.routes import auth, download, get_user, realm, upload

logging.basicConfig(level="INFO")

app = FastAPI()

# ВАЖНО: Starlette.add_middleware() вставляет каждый новый middleware В НАЧАЛО списка
# (self.user_middleware.insert(0, ...)), поэтому ПОСЛЕДНИЙ добавленный middleware
# становится САМЫМ ВНЕШНИМ и выполняется ПЕРВЫМ на входящем запросе.
# Чтобы AuthMiddleware мог читать уже заполненный SessionMiddleware scope["session"],
# нужно добавить AuthMiddleware ПЕРВЫМ (он будет внутренним),
# а SessionMiddleware — ПОСЛЕДНИМ (он будет внешним и отработает раньше).


# Middleware для проверки авторизации — добавляем ПЕРВЫМ (станет innermost)
class AuthMiddleware:
    """Middleware для проверки авторизации на всех страницах, кроме login/logout/callback."""

    public_paths = ["/login", "/callback", "/logout"]

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        from starlette.requests import Request
        from starlette.responses import RedirectResponse

        request = Request(scope, receive)

        # Публичные пути — пропускаем без проверки
        if request.url.path in self.public_paths:
            await self.app(scope, receive, send)
            return

        # Проверяем авторизацию через session из scope (уже инициализирован SessionMiddleware)
        if "user_email" not in scope.get("session", {}):
            # Не авторизован — редиректим на login
            redirect = RedirectResponse(url="/login", status_code=307)
            await redirect(scope, receive, send)
        else:
            await self.app(scope, receive, send)


app.add_middleware(AuthMiddleware)

# Middleware сессий — добавляем ПОСЛЕДНИМ (станет outermost и отработает первым,
# заполнив scope["session"] до того, как до него доберётся AuthMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "super-secret-key-change-me"),
)

templates = Jinja2Templates(directory="app/templates")


@app.get("/")
def root(request: Request):
    # Обработка параметров для отображения сообщений
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
            stats = f"Создано: {created}, Обновлено: {updated}, Пропущено: {skipped}"
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
            stats = f"Создано: {created}, Обновлено: {updated}, Пропущено: {skipped}"
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

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "message": message,
            "stats": stats,
            "selected_realm": request.query_params.get("realm"),
        },
    )


app.include_router(get_user.router)
app.include_router(upload.router)
app.include_router(download.router)
app.include_router(auth.router)
app.include_router(realm.router)


# Реalm-лист грузим лениво (не при старте приложения, а при первом запросе)
realm_list = []

templates.env.globals["realm"] = realm_list
templates.env.globals["user"] = lambda key, default="": ""
