import pytest
from mcdreforged.api.command import Literal

from sakura_flow.cli_entry import _parse_field_filters
from sakura_flow.help_core import get_commands, render_cli
from sakura_flow.mcdr_entry import _parse_search_criteria, register_mcdr_commands


def test_command_registration_builds_root_literal(mock_server, mock_service):
    try:
        register_mcdr_commands(mock_server, mock_service)
    except Exception as exc:
        pytest.fail(f"命令注册失败: {exc}")

    assert mock_server.register_command.called, "未调用 server.register_command"
    node_root = mock_server.register_command.call_args[0][0]
    assert isinstance(node_root, Literal)


def test_parse_search_criteria_uses_alias_tables():
    criteria = _parse_search_criteria("title=反应堆 s=!Done t=IV p=High collab=Steve l=工业")

    assert criteria["title"] == "反应堆"
    assert criteria["status"] == "!Done"
    assert criteria["tier"] == "IV"
    assert criteria["priority"] == "High"
    assert criteria["collaborator"] == "Steve"
    assert criteria["label"] == "工业"


def test_parse_search_criteria_defaults_plain_token_to_title():
    criteria = _parse_search_criteria("刷铁机")
    assert criteria == {"title": "刷铁机"}


def test_parse_search_criteria_supports_creator_canonical_key():
    criteria = _parse_search_criteria("creator=Alice")
    assert criteria == {"creator": "Alice"}


def test_parse_search_criteria_preserves_unknown_custom_key():
    criteria = _parse_search_criteria("machine_stage=mid")
    assert criteria == {"machine_stage": "mid"}


def test_parse_field_filters_accepts_multiple_pairs():
    criteria, err = _parse_field_filters(["machine_stage=mid", "owner_group=ops"])
    assert err is None
    assert criteria == {
        "machine_stage": "mid",
        "owner_group": "ops",
    }


def test_parse_field_filters_rejects_missing_equal_sign():
    criteria, err = _parse_field_filters(["badvalue"])
    assert criteria == {}
    assert err is not None


def test_parse_field_filters_rejects_empty_key_or_value():
    criteria, err = _parse_field_filters(["=x"])
    assert criteria == {}
    assert err is not None

    criteria, err = _parse_field_filters(["x="])
    assert criteria == {}
    assert err is not None


def test_help_catalog_contains_core_commands():
    commands = {item.name for item in get_commands()}
    assert "list" in commands
    assert "set" in commands
    assert "append" in commands


def test_help_catalog_topic_filter_supports_alias():
    commands = get_commands("l")
    assert len(commands) == 1
    assert commands[0].name == "list"


def test_render_cli_help_includes_same_command_surface():
    output = render_cli()
    assert "list" in output
    assert "append" in output
    assert "MCDR: !!sf list [page]" in output
