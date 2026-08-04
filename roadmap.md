# Roadmap: Keycloak Admin Wrapper (FastAPI + SQLite)

## Оглавление
1. Архитектура
2. Решения
3. Этап 0: Окружение
4. Этап 1: Адаптеры
5. Этап 2: Use Cases и БД
6. Этап 3: Представление
7. Этап 4: Безопасность
8. Этап 5: Упаковка
9. Тестирование и отладка

---

## 1. Архитектура

**Цель:** Прослойка для массового управления пользователями Keycloak через CSV с логированием.

**Стиль:** Порты и адаптеры (шестиугольная). Бизнес-логика (Use Cases) не зависит от внешних систем.

---

## 2. Ключевые решения

- **Авторизация:** Resource Owner Password через Keycloak (админ вводит свои креды).
- **Операции:** Сервисный аккаунт (Client Credentials) для стабильности.
- **Синхронность:** Без Celery, до 50 строк, обработка в HTTP-потоке.
- **Файлы:** На диске (`/storage/uploads/`), в БД только путь.
- **Тесты:** Unit (моки) и интеграционные (реальный Keycloak).

---

## 3. Этап 0: Подготовка

- [ ] Создать структуру:
keycloak_panel/
├── app/
│ ├── api/ (routes, dependencies)
│ ├── core/ (config, database)
│ ├── domain/ (dto, enums)
│ ├── application/ (use_cases)
│ ├── infrastructure/ (adapters)
│ ├── models/ (sqlalchemy)
│ ├── templates/ (jinja2)
│ └── static/
├── storage/uploads/
├── tests/ (unit, integration)
├── .env
├── docker-compose.yml
├── Dockerfile
└── requirements.txt

- [ ] Написать `docker-compose.yml` с Keycloak 24 + Postgres 15, запустить.
- [ ] В Keycloak создать клиента `my_admin_service` с `Client authentication`, в `Service Account Roles` дать `manage-users` для `realm-management`. Скопировать Secret.
- [ ] Создать `.env`:

KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=master
SERVICE_CLIENT_ID=my_admin_service
SERVICE_CLIENT_SECRET=...
DATABASE_URL=sqlite:///./app.db
SECRET_KEY=...
DEBUG=True
MOCK_KEYCLOAK=False


- [ ] Установить зависимости: `fastapi[standard]`, `uvicorn`, `sqlalchemy`, `python-keycloak`, `python-dotenv`, `jinja2`, `python-multipart`, `passlib[bcrypt]`, `alembic`, `pytest`, `pytest-asyncio`, `requests`.

---

## 4. Этап 1: Инфраструктура (Адаптеры)

- [ ] **KeycloakAdapter** (`app/infrastructure/keycloak_adapter.py`):
  - `__init__` через `client_id/secret`.
  - `create_user(realm, payload)`, `delete_user(realm, username)`, `get_user_id(realm, username)`, `get_users(realm)`.
  - **Тест:** интеграционный – реальный Keycloak.
- [ ] **DTO** (`app/domain/dto.py`): `UserImportDTO` (username, email, first_name, last_name, password, action).
- [ ] **CSV Parser** (`app/infrastructure/csv_parser.py`): `parse_users_csv(file_path) -> list[UserImportDTO]`. По умолчанию action = `create`.
  - **Тест:** unit – через `StringIO`.
- [ ] **FileStorage** (`app/infrastructure/file_storage.py`): `save_upload_file(upload_file, realm) -> str` (сохраняет в `storage/uploads/{realm}_{timestamp}_{filename}`).

---

## 5. Этап 2: Приложение (Use Cases) и БД

- [ ] **Модели SQLAlchemy** (`app/models/`):
  - `UploadedFile`: id, realm, file_path, status (pending/processing/completed/failed), total_rows, uploaded_by, created_at.
  - `AuditLog`: id, upload_id (FK), row_number, username, intended_action, result (success/error), keycloak_response, created_at.
- [ ] Настроить Alembic, создать и применить миграцию.
  - **Тест:** unit с SQLite `:memory:`.
- [ ] **Репозитории** (`app/infrastructure/repositories/`):
  - `UploadRepo`: create, update_status.
  - `AuditRepo`: bulk_create_logs.
- [ ] **ImportUsersUseCase** (`app/application/use_cases/import_users.py`):
  - Парсит CSV, для каждого DTO вызывает адаптер (с try/except), собирает логи, сохраняет через репозиторий, обновляет статус файла.
  - **Тест:** unit с моками адаптера и репозитория.

---

## 6. Этап 3: Представление (FastAPI + Jinja2)

- [ ] **Роуты** (`app/api/routes/admin_routes.py`):
  - `GET /dashboard` – форма выбора реалма и загрузки файла.
  - `POST /upload` – сохраняет файл, создаёт запись в БД, вызывает Use Case синхронно, рендерит `result.html` с таблицей логов.
  - `GET /history` – список всех загрузок с пагинацией.
- [ ] **Шаблоны:** `base.html`, `dashboard.html`, `result.html`, `history.html` (Bootstrap).
- [ ] **Тест E2E:** через `TestClient` загрузить CSV, проверить ответ и записи в БД.

---

## 7. Этап 4: Безопасность (Авторизация через Keycloak)

- [ ] **LoginUseCase** (`app/application/use_cases/login_user.py`):
  - Отправляет `username/password` в `/token` эндпоинт Keycloak, получает JWT, парсит `preferred_username` и список реалмов из `realm_access`.
  - Возвращает `UserSession(username, realms)`.
- [ ] **Зависимости** (`app/api/dependencies/auth.py`):
  - `get_current_user(request)` – читает сессию, иначе 401.
  - `check_realm_access(request, realm)` – проверяет, что реалм есть в сессии, иначе 403.
- [ ] **Роуты логина:**
  - `GET /login` – форма.
  - `POST /login` – вызывает LoginUseCase, сохраняет в сессию, редирект на `/dashboard`.
  - `GET /logout` – очищает сессию.
- [ ] Навесить `Depends(get_current_user)` на все админские роуты, `Depends(check_realm_access)` на `/upload`.
- [ ] **Тест:** unit – мок ответа Keycloak с токеном.

---

## 8. Этап 5: Финальная упаковка

- [ ] **Dockerfile:**
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


- [ ] Обновить `docker-compose.yml`, добавив сервис `app` с портом 8000 и томами для `storage` и `app.db`.
- [ ] **Smoke-тест:** `docker-compose up --build`, войти, загрузить CSV, проверить создание пользователей и историю.

---

## 9. Тестирование и отладка

- **Режим MOCK:** в `.env` `MOCK_KEYCLOAK=True`, в адаптере проверять и возвращать фиктивные данные.
- **Быстрая проверка:** `if __name__ == "__main__"` в адаптере для прямого запуска.
- **Структура тестов:**


tests/
├── conftest.py
├── unit/
│ ├── test_csv_parser.py
│ ├── test_use_case.py
│ └── test_auth.py
└── integration/
├── test_keycloak_adapter.py
└── test_api.py


- **Логи:** `logging.DEBUG` в `main.py`, добавлять `logger.debug()` в Use Cases.
- **Запуск тестов:** `pytest -v`.

---

## Итоговый чек-лист

- [ ] Keycloak в Docker с сервисным аккаунтом.
- [ ] Адаптер Keycloak работает.
- [ ] Есть загрузка CSV, история, логи в БД.
- [ ] Авторизация через Keycloak.
- [ ] Написаны тесты.
- [ ] Проект собирается в Docker и запускается.
