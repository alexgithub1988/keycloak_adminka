from starlette.requests import Request
from starlette.responses import RedirectResponse


class AuthMiddleware:
    """Middleware для проверки авторизации на всех страницах, кроме login/logout/callback."""

    public_paths = ["/login", "/callback", "/logout"]

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

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
