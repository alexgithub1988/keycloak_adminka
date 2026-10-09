#!/usr/bin/env python3
import os
import sys
import time

import requests

# Ждём пока Keycloak поднимется (до 120 секунд)
for i in range(120):
    try:
        resp = requests.get(
            "http://keycloak:8080/realms/master/.well-known/openid-configuration",
            timeout=2,
        )
        if resp.status_code == 200:
            print("✓ Keycloak ready")
            time.sleep(2)  # Даём ещё пару секунд на инициализацию
            break
    except Exception as e:
        if i % 10 == 0:
            print(f"Waiting for Keycloak... ({i+1}/120) - {type(e).__name__}")
    time.sleep(1)
else:
    print("✗ Keycloak не поднялся за 120 секунд")
    sys.exit(1)

# Получаем токен администратора
token_url = "http://keycloak:8080/realms/master/protocol/openid-connect/token"
token_data = {
    "username": "admin",
    "password": "admin",
    "grant_type": "password",
    "client_id": "admin-cli",
}

resp = requests.post(token_url, data=token_data)
if resp.status_code != 200:
    print(f"Не удалось получить токен: {resp.text}")
    sys.exit(1)

token = resp.json()["access_token"]
print("✓ Got admin token")

# Создаём/обновляем клиент
client_secret = os.getenv(
    "CLIENT_SECRET",
    "xk6m0BdiI6e5R4iMiI0a1unwCLgPA4Lxr2RCGjtdXyCLEgbhUTvmKQUWLsTSNUSAUYbgCMXY3UTUpKo2IGYC4Y",
)

client_data = {
    "clientId": "my_app",
    "name": "My App",
    "enabled": True,
    "publicClient": False,
    "protocol": "openid-connect",
    "redirectUris": ["http://localhost:8000/callback"],
    "webOrigins": ["http://localhost:8000"],
    "standardFlowEnabled": True,
    "implicitFlowEnabled": False,
    # Post-logout redirect URI задаётся через атрибут клиента, а не отдельное
    # поле ClientRepresentation: в Keycloak 24 поле postLogoutRedirectUris
    # отсутствует в REST API и вызывает ошибку "Unrecognized field".
    "attributes": {
        "post.logout.redirect.uris": "http://localhost:8000/",
    },
}

client_url = "http://keycloak:8080/admin/realms/master/clients"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Проверяем есть ли уже такой клиент
list_resp = requests.get(client_url + "?clientId=my_app", headers=headers)
existing = list_resp.json() if list_resp.status_code == 200 else []

if existing:
    # Клиент уже есть — обновляем его настройки (redirectUris, webOrigins,
    # attributes с post.logout.redirect.uris и т.д.), чтобы они всегда совпадали
    # с init_keycloak.py. Секрет при обновлении НЕ меняется: Keycloak хранит его
    # хэшированным и не принимает новое значение через PUT.
    client_id = existing[0]["id"]
    update_resp = requests.put(
        client_url + f"/{client_id}", json=client_data, headers=headers
    )
    if update_resp.status_code in [204, 200]:
        print("✓ Client my_app updated")
    else:
        print(f"Не удалось обновить клиент: {update_resp.text}")
        sys.exit(1)
else:
    # Создаём новый клиент (секрет задаётся только при создании)
    create_payload = {**client_data, "secret": client_secret}
    create_resp = requests.post(client_url, json=create_payload, headers=headers)
    if create_resp.status_code in [201, 200]:
        print("✓ Client my_app created")
    else:
        print(f"Не удалось создать клиент: {create_resp.text}")
        sys.exit(1)

print("✓ Keycloak initialized successfully")
