import logging

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

from app.api.routes import download, get_user, upload
from app.infrastructure.keycloack_adapter import KeycloakAdminAdapter

logging.basicConfig(level="INFO")

app = FastAPI()

templates = Jinja2Templates(directory="app/templates")


@app.get("/")
def root(request: Request):
    # Обработка параметров для отображения сообщений
    message = None
    if "success" in request.query_params:
        if request.query_params.get("success") == "upload_complete":
            message = {
                "type": "success",
                "icon": "check-circle-fill",
                "text": "Файл успешно загружен и пользователи созданы!",
            }
    elif "error" in request.query_params:
        if request.query_params.get("error") == "csv_only":
            message = {
                "type": "danger",
                "icon": "exclamation-triangle-fill",
                "text": "Разрешены только CSV файлы!",
            }

    return templates.TemplateResponse(request, "index.html", {"message": message})


app.include_router(get_user.router)
app.include_router(upload.router)
app.include_router(download.router)

admin = KeycloakAdminAdapter("master")
realm_list = admin.get_realms_list()
logging.info(f"{realm_list}")
templates.env.globals["realm"] = realm_list
