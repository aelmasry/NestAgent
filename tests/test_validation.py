from harness.validation import validate_tool_spec


def test_validate_tool_spec_requires_fields():
    result = validate_tool_spec({"name": "x"}, set())
    assert not result.approved
    assert result.reasons
