from sakura_flow.application import TodoApplication


class FakeRepo:
    def __init__(self):
        self.definitions = {
            "machine_stage": {
                "key_name": "machine_stage",
                "value_kind": "enum",
                "is_required": False,
                "default_value": None,
                "enum_values": ["early", "mid", "late"],
            },
            "owner_group": {
                "key_name": "owner_group",
                "value_kind": "scalar",
                "is_required": False,
                "default_value": None,
                "enum_values": [],
            },
            "labels": {
                "key_name": "labels",
                "value_kind": "list",
                "is_required": False,
                "default_value": None,
                "enum_values": [],
            },
            "required_code": {
                "key_name": "required_code",
                "value_kind": "scalar",
                "is_required": True,
                "default_value": None,
                "enum_values": [],
            },
        }

    def get_field_definition(self, key_name: str):
        return self.definitions.get(str(key_name).strip().lower())

    def set_field_default(self, key_name: str, default_value: str) -> bool:
        key = str(key_name).strip().lower()
        definition = self.definitions.get(key)
        if definition is None:
            return False
        definition["default_value"] = default_value
        return True


class FailingRepo(FakeRepo):
    def set_field_default(self, key_name: str, default_value: str) -> bool:
        return False


def test_set_field_default_enum_success_with_case_insensitive_value():
    app = TodoApplication(FakeRepo())

    success, normalized, err = app.set_field_default("machine_stage", "MID")

    assert success is True
    assert normalized == "mid"
    assert err is None


def test_set_field_default_rejects_list_field():
    app = TodoApplication(FakeRepo())

    success, normalized, err = app.set_field_default("labels", "industrial")

    assert success is False
    assert normalized is None
    assert err == "default_not_allowed"


def test_set_field_default_rejects_title_and_creator():
    app = TodoApplication(FakeRepo())

    title_result = app.set_field_default("title", "x")
    creator_result = app.set_field_default("creator", "x")

    assert title_result == (False, None, "default_not_allowed")
    assert creator_result == (False, None, "default_not_allowed")


def test_set_field_default_rejects_required_scalar_field():
    app = TodoApplication(FakeRepo())

    success, normalized, err = app.set_field_default("required_code", "A1")

    assert success is False
    assert normalized is None
    assert err == "default_not_allowed"


def test_set_field_default_rejects_invalid_enum_value():
    app = TodoApplication(FakeRepo())

    success, normalized, err = app.set_field_default("machine_stage", "invalid")

    assert success is False
    assert normalized is None
    assert err == "invalid_enum_default_value"


def test_set_field_default_accepts_enum_index_id():
    app = TodoApplication(FakeRepo())

    success, normalized, err = app.set_field_default("machine_stage", "2")

    assert success is True
    assert normalized == "late"
    assert err is None


def test_set_field_default_reports_persist_failure():
    app = TodoApplication(FailingRepo())

    success, normalized, err = app.set_field_default("owner_group", "ops")

    assert success is False
    assert normalized is None
    assert err == "persist_failed"

