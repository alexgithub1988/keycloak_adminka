import logging

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.infrastructure.auth_service import auth_service

router = APIRouter()

logger = logging.getLogger(__name__)


def _get_redirect_uri(request: Request) -> str:
    """Формирует redirect_uri на основе текущего запроса."""
    # Берём host и port из запроса, чтобы redirect_uri совпадал с тем,
    # который зарегистрирован в Keycloak
    scheme = "https" if request.url.scheme == "https" else "http"
    host = request.url.hostname or "localhost"
    port = request.url.port or 8000
    return f"{scheme}://{host}:{port}/callback"


@router.get("/login")
async def login(request: Request):
    """Перенаправляет на страницу авторизации Keycloak."""
    import secrets

    redirect_uri = _get_redirect_uri(request)
    # Генерируем state для защиты от CSRF атак
    state = secrets.token_urlsafe(32)
    try:
        auth_url = auth_service.get_authorization_url(redirect_uri, state=state)
        request.session["auth_state"] = state
        return RedirectResponse(url=auth_url)
    except Exception as e:
        logger.error(f"Ошибка при создании URL авторизации: {e}")
        return RedirectResponse(url="/?error=auth_error", status_code=303)


@router.get("/callback")
async def callback(request: Request):
    """Обработка callback от Keycloak: обмен code на token."""
    redirect_uri = _get_redirect_uri(request)

    code = request.query_params.get("code")
    error = request.query_params.get("error")
    state = request.query_params.get("state")
    stored_state = request.session.pop("auth_state", "")  # используем и удаляем

    if error:
        logger.error(f"Ошибка авторизации от Keycloak: {error}")
        return RedirectResponse(url="/?error=login_failed", status_code=303)

    if not code:
        logger.error("Code не получен от Keycloak")
        return RedirectResponse(url="/?error=login_failed", status_code=303)

    # Валидация state для защиты от CSRF атак
    if not auth_service.validate_state(stored_state, state):
        logger.error("Ошибка валидации state (CSRF защита)")
        return RedirectResponse(url="/?error=login_failed", status_code=303)

    try:
        # Обмениваем code на token
        token_response = auth_service.exchange_code_for_token(code, redirect_uri)

        # ВАЖНО: передаём id_token, а не access_token.
        # id_token — это JWT с claims пользователя, который декодируется через JWKS.
        # access_token — токен для API, у него другой kid и другие claims.
        user_info = auth_service.get_user_info(token_response.get("id_token", ""))
        if user_info:
            request.session["user_email"] = user_info.get("email", "")
            request.session["user_name"] = user_info.get("preferred_username", "User")
            request.session["user_id"] = user_info.get("sub", "")

        # ВАЖНО: не сохраняем access_token/refresh_token в сессии.
        # JWT токены Keycloak слишком большие (1-3 КБ каждый) и вместе
        # с metadata дают cookie > 4096 байт — браузер тихо отбрасывает
        # такие Set-Cookie (RFC 6265). SessionMiddleware от Starlette хранит
        # всё в cookie (без server-side storage), поэтому превышение лимита
        # приводит к пустой сессии и бесконечному циклу редиректов.
        # Для админ-операций (upload, get_user) используется KeycloakAdminAdapter,
        # который получает токен через admin-credentials заново.

        # Редиректим на главную
        return RedirectResponse(url="/", status_code=303)

    except Exception as e:
        logger.error(f"Ошибка при обмене code на token: {e}")
        return RedirectResponse(url="/?error=login_failed", status_code=303)


@router.get("/logout")
async def logout(request: Request):
    """Выход из системы — очищает сессию и редиректит на Keycloak logout."""
    redirect_uri = _get_redirect_uri(request)

    # Очищаем сессию
    request.session.clear()

    # Редиректим на Keycloak logout — чтобы выйти и из Keycloak тоже
    logout_url = auth_service.get_logout_url(redirect_uri.replace("/callback", "/"))
    response = RedirectResponse(url=logout_url, status_code=303)
    # Удаляем cookie сессии
    response.delete_cookie("session", path="/")
    return response
