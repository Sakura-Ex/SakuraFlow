from sakura_flow.interface import UI


class DummyServer:
    def tr(self, key, *args):
        mapping = {
            "sakuraflow.prop.status": "任务状态",
            "sakuraflow.prop.labels": "任务标签",
        }
        if key in mapping:
            return mapping[key]
        if args:
            return key + " " + " ".join(str(arg) for arg in args)
        return key


def test_prop_label_uses_translation_only_for_builtin_fields():
    server = DummyServer()

    assert UI._prop_label(server, "status") == "任务状态"
    assert UI._prop_label(server, "labels") == "任务标签"
    assert UI._prop_label(server, "owner_group") == "owner_group"


def test_hover_info_includes_labels_and_custom_fields():
    server = DummyServer()
    task = {
        "title": "Build Reactor",
        "creator": "Alice",
        "status": "In Progress",
        "tier": "MV",
        "priority": "High",
        "labels": ["energy", "industrial"],
        "dependencies": [],
        "collaborators": [],
        "notes": [],
        "custom": {
            "owner_group": "ops",
        },
        "custom_lists": {
            "watchers": ["Bob", "Carol"],
        },
    }

    hover = UI.create_hover_info("1", task, {}, server)
    text = str(hover)

    assert "任务标签" in text
    assert "energy" in text
    assert "owner_group" in text
    assert "ops" in text
    assert "watchers" in text
    assert "Bob" in text


def test_render_task_info_includes_labels_and_custom_fields():
    server = DummyServer()
    task = {
        "title": "Build Reactor",
        "creator": "Alice",
        "description": "",
        "status": "In Progress",
        "tier": "MV",
        "priority": "High",
        "labels": ["energy"],
        "collaborators": [],
        "dependencies": [],
        "notes": [],
        "custom": {
            "owner_group": "ops",
        },
        "custom_lists": {
            "watchers": ["Bob"],
        },
    }

    info = UI.render_task_info("1", task, {"1": task}, server)
    text = str(info)

    assert "任务标签" in text
    assert "energy" in text
    assert "owner_group" in text
    assert "ops" in text
    assert "watchers" in text
    assert "Bob" in text
