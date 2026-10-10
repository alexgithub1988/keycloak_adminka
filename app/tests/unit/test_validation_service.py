import pytest

from app.infrastructure.keycloak_admin.validation_service import ValidationService


@pytest.mark.parametrize(
    "value,field_type, expected",
    [
        ("101", "integer", True),
    ],
)
def test_check_type(value, field_type, expected):
    assert ValidationService._check_type(value, field_type) is expected


@pytest.mark.parametrize(
    "rule_name,ref,expected",
    [("Basic", "Basic", True), ("Basic", "Basic2", False), ("/Test", "/Test", True)],
)
def test_group_ref_matched(rule_name, ref, expected):
    assert ValidationService._group_ref_matches(rule_name, ref) is expected
