import json
import os

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
