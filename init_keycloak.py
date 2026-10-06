#!/usr/bin/env python3
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

# Создаём клиент
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
    "secret": "xk6m0BdiI6e5R4iMiI0a1unwCLgPA4Lxr2RCGjtdXyCLEgbhUTvmKQUWLsTSNUSAUYbgCMXY3UTUpKo2IGYC4Y",
}

client_url = "http://keycloak:8080/admin/realms/master/clients"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Проверяем есть ли уже такой клиент
list_resp = requests.get(client_url + "?clientId=my_app", headers=headers)
if list_resp.status_code == 200 and list_resp.json():
    print("✓ Client my_app already exists")
else:
    # Создаём новый
    create_resp = requests.post(client_url, json=client_data, headers=headers)
    if create_resp.status_code in [201, 200]:
        print("✓ Client my_app created")
    else:
        print(f"Не удалось создать клиент: {create_resp.text}")
        sys.exit(1)

print("✓ Keycloak initialized successfully")
