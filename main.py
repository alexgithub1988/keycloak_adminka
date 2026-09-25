import logging
import os

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.api.routes import audit, auth, download, get_user, realm, upload
from app.infrastructure.message_handler import MessageHandler
from app.infrastructure.middleware_auth import AuthMiddleware
from app.infrastructure.models import Base, engine

# Create all tables
Base.metadata.create_all(bind=engine)

logging.basicConfig(level="INFO")

app = FastAPI()

# ВАЖНО: Starlette.add_middleware() вставляет каждый новый middleware В НАЧАЛО списка
# (self.user_middleware.insert(0, ...)), поэтому ПОСЛЕДНИЙ добавленный middleware
# становится САМЫМ ВНЕШНИМ и выполняется ПЕРВЫМ на входящем запросе.
# Чтобы AuthMiddleware мог читать уже заполненный SessionMiddleware scope["session"],
# нужно добавить AuthMiddleware ПЕРВЫМ (он будет внутренним),
# а SessionMiddleware — ПОСЛЕДНИМ (он будет внешним и отработает раньше).


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
    message, stats = MessageHandler.process_request_messages(request)

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
app.include_router(audit.router)

# Реalm-лист грузим лениво (не при старте приложения, а при первом запросе)
realm_list = []

templates.env.globals["realm"] = realm_list
templates.env.globals["user"] = lambda key, default="": ""
