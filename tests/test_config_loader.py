from sakura_flow.config_loader import (
    apply_custom_field_definitions,
    ensure_custom_fields_config,
    load_custom_field_definitions,
)
from sakura_flow.manager import TodoManager


def test_load_custom_fields_rejects_core_key(tmp_path):
    config_path = tmp_path / "custom_fields.yml"
    config_path.write_text(
        """
version: 1
custom_fields:
  - key_name: tier
    value_kind: enum
    options: [LV, MV]
""".strip(),
        encoding="utf-8",
    )

    definitions, warnings = load_custom_field_definitions(str(config_path))
    assert definitions == []
    assert any("protected core field" in warning for warning in warnings)


def test_apply_custom_fields_registers_defaults(tmp_path):
    db_path = tmp_path / "tasks.db"
    manager = TodoManager(str(db_path))

    config_path = tmp_path / "custom_fields.yml"
    config_path.write_text(
        """
version: 1
custom_fields:
  - key_name: machine_stage
    value_kind: enum
    default_value: mid
    enum_values: [early, mid, late]
  - key_name: owner_group
    value_kind: scalar
    default_value: ops
""".strip(),
        encoding="utf-8",
    )

    warnings = apply_custom_field_definitions(manager, str(config_path))
    assert warnings == []

    task_id = manager.add_task("Config default test", "Alice")
    task = manager.get_task(task_id)
    assert task is not None
    assert task["custom"]["machine_stage"] == "mid"
    assert task["custom"]["owner_group"] == "ops"


def test_ensure_config_copies_template_with_comments(tmp_path):
    config_path = tmp_path / "custom_fields.yml"
    template_path = tmp_path / "template.yml"
    template_text = "# comment line\nversion: 1\ncustom_fields: []\n"
    template_path.write_text(template_text, encoding="utf-8")

    ensure_custom_fields_config(str(config_path), template_path=str(template_path))

    assert config_path.exists()
    assert config_path.read_text(encoding="utf-8") == template_text


def test_ensure_config_does_not_overwrite_existing_file(tmp_path):
    config_path = tmp_path / "custom_fields.yml"
    config_path.write_text("version: 1\ncustom_fields: []\n", encoding="utf-8")

    template_path = tmp_path / "template.yml"
    template_path.write_text("# new template\nversion: 1\ncustom_fields: []\n", encoding="utf-8")

    ensure_custom_fields_config(str(config_path), template_path=str(template_path))

    assert config_path.read_text(encoding="utf-8") == "version: 1\ncustom_fields: []\n"
