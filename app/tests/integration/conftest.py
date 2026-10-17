import os
from uuid import uuid4

import pytest
import requests
from dotenv import load_dotenv

from app.infrastructure.keycloak_adapter import KeycloakAdminAdapter
from app.infrastructure.keycloak_admin.connection import KeycloakConnection

load_dotenv()


@pytest.fixture(scope="session")
def keycloack_is_avalable():
    """Проверка включен ли кейклок перед стартом прогона"""
    url = os.getenv("KEYCLOACK_URL", "http://localhost:8080")
    try:
        resp = requests.get(f"{url}/realms/master", timeout=5)
        resp.raise_for_status()
    except requests.RequestException as e:
        pytest.skip(f"KC  не доступен {e}")


@pytest.fixture(scope="session")
def master_admin(keycloack_is_avalable):
    return KeycloakConnection("master").admin


@pytest.fixture(scope="session")
def realm(master_admin):
    name = f"test-integration-{uuid4().hex[:8]}"
    master_admin.create_realm({"realm": name, "enabled": True})
    yield name
    master_admin.delete_realm(name)


@pytest.fixture(scope="session")
def seeded_user(realm):
    admin = KeycloakConnection(realm).admin
    suffix = uuid4().hex[:8]
    user = {
        "email": f"seed-{suffix}@example.com",
        "username": f"seed-{suffix}",
        "firstName": "Seed",
        "lastName": "User",
        "enabled": True,
    }
    admin.create_user(user)
    return user


@pytest.fixture(scope="session")
def seeded_group(realm):
    admin = KeycloakConnection(realm).admin
    group = {"name": f"group-{uuid4().hex[:8]}"}
    admin.create_group(group)
    return group


@pytest.fixture(scope="session")
def adapter(realm):
    return KeycloakAdminAdapter(realm)
