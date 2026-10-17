import pytest

from app.infrastructure.keycloak_adapter import KeycloakAdminAdapter


@pytest.mark.integration
def test_get_realms_list(realm):
    realms = KeycloakAdminAdapter("master").get_realms_list()
    assert "master" in realms
    assert realm in realms
