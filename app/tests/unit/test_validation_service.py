import pytest

from app.infrastructure.keycloak_admin.validation_service import ValidationService


@pytest.mark.parametrize(
    "value,field_type, expected",
    [
        ("101", "integer", True),
        ("true", "boolean", True),
        ("false", "boolean", True),
        ("name", "string", True),
        ("102", "boolean", False),
        ("103", "string", True),
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


def test_get_rules_from_db(db_session):
    service = ValidationService(db=db_session, realm="test")
    assert service.get_rules() == []


def test_get_rules_filers_by_realm(db_session, make_rule):
    make_rule(rule_type="attribute", rule_name="test1", realm="test1")
    make_rule(rule_type="group", rule_name="group", realm="test2")

    rules = ValidationService(db=db_session, realm="test1").get_rules()
    assert [r.rule_name for r in rules] == ["test1"]
