from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

from app.api.routes import get_user, upload

app = FastAPI()


templates = Jinja2Templates(directory="app/templates")


@app.get("/")
def root(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
    )


app.include_router(get_user.router)
app.include_router(upload.router)
