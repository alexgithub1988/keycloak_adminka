import pytest


@pytest.mark.integration
def test_get_users_return_seeded(adapter, seeded_user):
    users = adapter.get_users()
    emails = [u.get("email") for u in users]
    assert seeded_user["email"] in emails


@pytest.mark.integration
def test_find_user_finds_seeded(adapter, seeded_user):
    found = adapter.find_user(
        seeded_user["email"],
        seeded_user["username"],
        seeded_user["firstName"],
        seeded_user["lastName"],
    )
    assert found is not None
    assert found["email"] == seeded_user["email"]


@pytest.mark.integration
def test_find_user_returns_none_for_unknown(adapter):
    found = adapter.find_user("nobody@example.com", "nobody", "", "")
    assert found is None
