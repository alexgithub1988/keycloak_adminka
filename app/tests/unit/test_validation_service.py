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


def test_get_rules(db_session, make_rule):
    """Тестим что пишем в базу и получаем"""
    make_rule(
        rule_type="attribute", rule_name="test1", realm="test1", description="test"
    )
    make_rule(
        rule_type="attribute",
        rule_name="test2",
        realm="test1",
        description="test",
        field_type="integer",
        is_required=True,
    )
    rules = ValidationService(db=db_session, realm="test1").get_rules()
    assert rules[0].rule_type == "attribute"
    assert rules[0].rule_name == "test1"
    assert rules[0].description == "test"
    assert rules[0].is_required is False
    assert rules[0].field_type == "string"
    assert rules[1].field_type == "integer"
    assert rules[1].is_required is True


def test_get_rules_filers_by_realm(db_session, make_rule):
    """Тут фильтрация по реалму"""
    make_rule(rule_type="attribute", rule_name="test1", realm="test1")
    make_rule(rule_type="group", rule_name="group", realm="test2")

    rules = ValidationService(db=db_session, realm="test1").get_rules()
    assert [r.rule_name for r in rules] == ["test1"]
    rules = ValidationService(db=db_session, realm="test2").get_rules()
    assert [r.rule_name for r in rules] == ["group"]
