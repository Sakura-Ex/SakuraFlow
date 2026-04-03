import json
import os

from sakura_flow.application.use_cases.task_mutations import append_list_property, set_property
from sakura_flow.manager import TodoManager


def test_sqlite_basic_crud(tmp_path):
    db_path = tmp_path / "tasks.db"
    manager = TodoManager(str(db_path))

    task_id = manager.add_task("Build Reactor", "Alice")
    assert manager.task_exists(task_id)

    assert manager.update_task(task_id, "priority", "High", "Alice")
    assert manager.update_task(task_id, "labels", "energy", "Alice")
    assert manager.add_note(task_id, "Started blueprint", "Alice")

    task = manager.get_task(task_id)
    assert task is not None
    assert task["priority"] == "High"
    assert task["labels"] == ["energy"]
    assert len(task["notes"]) == 1


def test_json_auto_migration_with_backup(tmp_path):
    data_dir = tmp_path / "sf_tasks"
    os.makedirs(data_dir, exist_ok=True)

    legacy_json = data_dir / "tasks.json"
    db_path = data_dir / "tasks.db"

    legacy_payload = {
        "tasks": {
            "1": {
                "title": "Legacy task",
                "creator": "Bob",
                "description": "",
                "status": "In Progress",
                "tier": "MV",
                "priority": "Medium",
                "labels": ["legacy"],
                "collaborators": ["Steve"],
                "dependencies": [],
                "notes": [{"time": "2026-01-01 10:00:00", "author": "Bob", "content": "old note"}],
                "created_at": "2026-01-01 09:00:00",
                "last_updated": "2026-01-01 10:00:00",
                "last_editor": "Bob",
            }
        },
        "next_id": 2,
        "default_tier": "HV",
    }
    legacy_json.write_text(json.dumps(legacy_payload, ensure_ascii=False), encoding="utf-8")

    manager = TodoManager(str(db_path), legacy_json_path=str(legacy_json))

    task = manager.get_task("1")
    assert task is not None
    assert task["title"] == "Legacy task"
    assert task["tier"] == "MV"
    assert task["labels"] == ["legacy"]
    assert manager.data["default_tier"] == "HV"
    assert os.path.exists(str(legacy_json) + ".bak")
    assert manager.startup_warning is None


def test_migration_failure_starts_with_empty_db_and_warning(tmp_path):
    data_dir = tmp_path / "sf_tasks"
    os.makedirs(data_dir, exist_ok=True)

    legacy_json = data_dir / "tasks.json"
    db_path = data_dir / "tasks.db"
    legacy_json.write_text("{broken json", encoding="utf-8")

    manager = TodoManager(str(db_path), legacy_json_path=str(legacy_json))

    assert manager.startup_warning is not None
    assert manager.get_all_tasks() == {}


def test_search_tasks_sql_exact_and_negation(tmp_path):
    db_path = tmp_path / "tasks.db"
    manager = TodoManager(str(db_path))

    t1 = manager.add_task("Build Reactor", "Alice")
    t2 = manager.add_task("Collect Titanium", "Bob")

    manager.update_task(t1, "status", "Done", "Alice")
    manager.update_task(t1, "labels", "energy", "Alice")
    manager.update_task(t2, "labels", "mining", "Bob")
    manager.update_task(t2, "collaborators", "Steve", "Bob")

    done_tasks = manager.search_tasks({"status": "Done"})
    assert list(done_tasks.keys()) == [t1]

    not_done_tasks = manager.search_tasks({"status": "!Done"})
    assert list(not_done_tasks.keys()) == [t2]

    by_label = manager.search_tasks({"label": "energy"})
    assert list(by_label.keys()) == [t1]

    not_by_collab = manager.search_tasks({"collaborator": "!Steve"})
    assert list(not_by_collab.keys()) == [t1]


def test_search_tasks_title_like_escapes_wildcards(tmp_path):
    db_path = tmp_path / "tasks.db"
    manager = TodoManager(str(db_path))

    t1 = manager.add_task("Need 100% Coverage", "Alice")
    manager.add_task("Need 100X Coverage", "Alice")

    results = manager.search_tasks({"title": "100%"})
    assert list(results.keys()) == [t1]


def test_task_cannot_depend_on_itself(tmp_path):
    db_path = tmp_path / "tasks.db"
    manager = TodoManager(str(db_path))

    task_id = manager.add_task("Self dependency test", "Alice")
    assert not manager.update_task(task_id, "dependencies", task_id, "Alice")
    task = manager.get_task(task_id)
    assert task is not None
    assert task.get("dependencies", []) == []


def test_append_list_property_returns_self_dependency_error(tmp_path):
    db_path = tmp_path / "tasks.db"
    manager = TodoManager(str(db_path))

    task_id = manager.add_task("Self dependency test", "Alice")
    success, err, arg = append_list_property(manager, task_id, "dependencies", task_id, "Alice")

    assert not success
    assert err == "sakuraflow.msg.self_dependency"
    assert arg == f"{task_id}->{task_id}({task_id}->{task_id})"


def test_task_cannot_form_indirect_dependency_cycle(tmp_path):
    db_path = tmp_path / "tasks.db"
    manager = TodoManager(str(db_path))

    a = manager.add_task("A", "Alice")
    b = manager.add_task("B", "Alice")
    c = manager.add_task("C", "Alice")

    assert manager.update_task(a, "dependencies", b, "Alice")
    assert manager.update_task(b, "dependencies", c, "Alice")
    assert not manager.update_task(c, "dependencies", a, "Alice")

    task_c = manager.get_task(c)
    assert task_c is not None
    assert task_c.get("dependencies", []) == []


def test_append_list_property_returns_cycle_path_error(tmp_path):
    db_path = tmp_path / "tasks.db"
    manager = TodoManager(str(db_path))

    a = manager.add_task("A", "Alice")
    b = manager.add_task("B", "Alice")

    assert manager.update_task(a, "dependencies", b, "Alice")

    success, err, cycle_path = append_list_property(manager, b, "dependencies", a, "Alice")
    assert not success
    assert err == "sakuraflow.msg.circular_dependency"
    assert cycle_path == f"{b}->{a}({b}->{b})" or cycle_path == f"{b}->{a}->{b}({b}->{b})"


def test_custom_scalar_and_enum_defaults_are_applied_on_create(tmp_path):
    db_path = tmp_path / "tasks.db"
    manager = TodoManager(str(db_path))

    assert manager.upsert_field_definition("owner_group", "scalar", default_value="ops")
    assert manager.upsert_field_definition(
        "machine_stage",
        "enum",
        default_value="mid",
        enum_values=["early", "mid", "late"],
    )

    task_id = manager.add_task("Defaulted task", "Alice")
    task = manager.get_task(task_id)

    assert task is not None
    assert task["custom"]["owner_group"] == "ops"
    assert task["custom"]["machine_stage"] == "mid"
    assert task["owner_group"] == "ops"
    assert task["machine_stage"] == "mid"


def test_all_configured_custom_fields_are_materialized_on_add(tmp_path):
    db_path = tmp_path / "tasks.db"
    manager = TodoManager(str(db_path))

    assert manager.upsert_field_definition("owner_group", "scalar", default_value="ops")
    assert manager.upsert_field_definition("machine_stage", "enum", default_value="mid", enum_values=["early", "mid", "late"])
    assert manager.upsert_field_definition("watchers", "list")
    assert manager.upsert_field_definition("notes_template", "scalar")

    task_id = manager.add_task("Materialized task", "Alice")
    task = manager.get_task(task_id)

    assert task is not None
    assert task["custom"]["owner_group"] == "ops"
    assert task["custom"]["machine_stage"] == "mid"
    assert task["custom"]["notes_template"] == ""
    assert task["custom_lists"]["watchers"] == []


def test_list_definition_has_no_default_and_roundtrip_works(tmp_path):
    db_path = tmp_path / "tasks.db"
    manager = TodoManager(str(db_path))

    assert manager.upsert_field_definition("watchers", "list", default_value="ignored")
    task_id = manager.add_task("List field test", "Alice")

    task = manager.get_task(task_id)
    assert task is not None
    assert "watchers" not in task.get("custom", {})

    assert manager.update_task(task_id, "watchers", "Steve", "Alice")
    assert manager.search_tasks({"watchers": "Steve"}).get(task_id) is not None
    assert manager.remove_item(task_id, "watchers", "Steve", "Alice")
    assert manager.search_tasks({"watchers": "Steve"}) == {}


def test_unknown_custom_field_is_rejected_until_registered(tmp_path):
    db_path = tmp_path / "tasks.db"
    manager = TodoManager(str(db_path))

    task_id = manager.add_task("Unknown field test", "Alice")
    assert not manager.update_task(task_id, "unregistered_key", "x", "Alice")

    assert manager.upsert_field_definition("unregistered_key", "scalar", default_value="")
    assert manager.update_task(task_id, "unregistered_key", "x", "Alice")


def test_custom_enum_without_default_falls_back_to_first_option(tmp_path):
    db_path = tmp_path / "tasks.db"
    manager = TodoManager(str(db_path))

    assert manager.upsert_field_definition("machine_stage", "enum", enum_values=["early", "mid", "late"])

    task_id = manager.add_task("Enum fallback test", "Alice")
    task = manager.get_task(task_id)
    assert task is not None
    assert task["custom"]["machine_stage"] == "early"


def test_set_field_default_accepts_enum_index_id(tmp_path):
    db_path = tmp_path / "tasks.db"
    manager = TodoManager(str(db_path))

    assert manager.upsert_field_definition("machine_stage", "enum", enum_values=["early", "mid", "late"])
    assert manager.set_field_default("machine_stage", "1")

    definition = manager.get_field_definition("machine_stage")
    assert definition is not None
    assert definition["default_value"] == "mid"


def test_set_property_rejects_invalid_custom_enum_with_specific_error(tmp_path):
    db_path = tmp_path / "tasks.db"
    manager = TodoManager(str(db_path))

    assert manager.upsert_field_definition(
        "machine_stage",
        "enum",
        default_value="mid",
        enum_values=["early", "mid", "late"],
    )
    task_id = manager.add_task("Enum validation", "Alice")

    success, _val, err = set_property(manager, task_id, "machine_stage", "invalid", "Alice")
    assert not success
    assert err == "sakuraflow.msg.invalid_enum_value"

    task = manager.get_task(task_id)
    assert task is not None
    assert task["machine_stage"] == "mid"


def test_set_property_keeps_builtin_enum_error_keys(tmp_path):
    db_path = tmp_path / "tasks.db"
    manager = TodoManager(str(db_path))

    task_id = manager.add_task("Builtin enum validation", "Alice")
    success, _val, err = set_property(manager, task_id, "priority", "not_a_priority", "Alice")

    assert not success
    assert err == "sakuraflow.msg.invalid_priority"
