import pytest


@pytest.mark.integration
def test_get_groups_returns_seeded(adapter, seeded_group):
    groups = adapter.get_groups()
    names = [g["name"] for g in groups]
    assert seeded_group["name"] in names
