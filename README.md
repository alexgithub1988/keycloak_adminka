

Для старта контейнера
```local keyclock start
sudo docker run -p 127.0.0.1:8080:8080 -e KC_BOOTSTRAP_ADMIN_USERNAME=admin -e KC_BOOTSTRAP_ADMIN_PASSWORD=admin quay.io/keycloak/keycloak:26.7.1 start-dev```

Версия 24.0.2
`sudo docker run --rm -p 127.0.0.1:8080:8080 \
  -e KEYCLOAK_ADMIN=admin \
  -e KEYCLOAK_ADMIN_PASSWORD=admin \
  quay.io/keycloak/keycloak:24.0.2 start-dev`



 с сохранением данных
 sudo docker run --rm -p 127.0.0.1:8080:8080 \
  -e KEYCLOAK_ADMIN=admin \
  -e KEYCLOAK_ADMIN_PASSWORD=admin \
  -v keycloak_data:/opt/keycloak/data \
  quay.io/keycloak/keycloak:24.0.2 start-dev

Тут также есть нюансы,во первых надо создать  в keycloack  приложение, второе передать его имя в .env  вместе с этим надо передать также и client_id  и вот тогда это будет работать и включить аутификацию тогда появятся креды в клиенте


Старт fastapi 'uvicorn main:app --reload --host 0.0.0.0 --port 8000'

## Запуск приложения через Docker

Приложение (FastAPI) контейнеризируется отдельно от Keycloak — это сделано специально,
чтобы можно было гибко переключаться между тестовым и боевым Keycloak, просто меняя
`.env`, без пересборки образа и без правок `docker-compose.yml`.

### 1. Настройте `.env`

Скопируйте `env_sample` в `.env` и заполните значениями. Ключевой момент — `KEYCLOAK_URL`:

- Если Keycloak поднят **на хосте** (например, командой `docker run` из раздела выше)
  и приложение тоже запускается **на хосте напрямую через `uvicorn`** —
  используйте `KEYCLOAK_URL=http://localhost:8080`.
- Если Keycloak поднят **на хосте**, а приложение запускается **в Docker-контейнере**
  (через `docker compose`) — используйте
  `KEYCLOAK_URL=http://host.docker.internal:8080`
  (алиас `host.docker.internal` уже прописан в `docker-compose.yml` через `extra_hosts`,
  поэтому работает и на Linux).
- Если Keycloak — **боевой**, доступный по реальному сетевому адресу/домену
  (не на локальном хосте) — просто укажите его настоящий URL,
  например `KEYCLOAK_URL=https://keycloak.example.com`. Никаких дополнительных
  правок Docker-файлов не требуется — контейнеру достаточно сетевого доступа наружу.

### 2. Соберите и запустите контейнер

```
docker compose up --build
```

Приложение будет доступно на `http://localhost:8000`.

### 3. Данные

Следующие пути монтируются как volume и переживают пересборки/перезапуски контейнера:

- `audit.db` — SQLite база (аудит операций, правила валидации реалмов);
- `upload_files/`, `download_files/`, `uploads/` — рабочие директории с CSV-файлами.

### 4. Пересборка после изменения зависимостей

Если менялся `requirements.txt`:

```
docker compose build --no-cache app
docker compose up
```
