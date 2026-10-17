from uuid import uuid4

import pytest


@pytest.mark.integration
def test_import_creates_new_user(adapter):
    suffix = uuid4().hex[:8]
    row = {
        "email": f"csv-{suffix}@example.com",
        "username": f"csv-{suffix}",
        "firstName": "Csv",
        "lastName": "User",
    }

    result = adapter.create_from_list([row])

    assert result["created"] == 1
    assert result["updated"] == 0
    assert result["errors"] == []


@pytest.mark.integration
def test_import_updates_existing_user(adapter):
    suffix = uuid4().hex[:8]
    row = {
        "email": f"csv-{suffix}@example.com",
        "username": f"csv-{suffix}",
        "firstName": "Csv",
        "lastName": "User",
    }

    adapter.create_from_list([row])
    result = adapter.create_from_list([row])

    assert result["created"] == 0
    assert result["updated"] == 1
    assert result["errors"] == []


@pytest.mark.integration
def test_import_with_unknown_group_is_error(adapter):
    suffix = uuid4().hex[:8]
    row = {
        "email": f"csv-{suffix}@example.com",
        "username": f"csv-{suffix}",
        "firstName": "Csv",
        "lastName": "User",
        "groups": "no-such-group",
    }

    result = adapter.create_from_list([row])

    assert result["created"] == 0
    assert result["skipped"] == 1
    assert len(result["errors"]) == 1
    assert "no-such-group" in result["errors"][0]


@pytest.mark.integration
def test_import_row_without_email_and_username_is_skipped(adapter):
    row = {"email": "", "username": ""}

    result = adapter.create_from_list([row])

    assert result["created"] == 0
    assert result["updated"] == 0
    assert result["skipped"] == 1
    assert result["errors"] == []
