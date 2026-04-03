from typing import Any, Callable, Optional

import warnings
from ...constants import LIST_PROP_ALIASES, PROP_ALIASES
from ...enums import Priority, Status, Tier
from ...ports.repository import TaskRepository


_ENUM_VALIDATORS: dict[str, tuple[Callable[[str], Optional[str]], str]] = {
    "tier": (Tier.validate, "sakuraflow.msg.invalid_tier"),
    "priority": (Priority.validate, "sakuraflow.msg.invalid_priority"),
    "status": (Status.validate, "sakuraflow.msg.invalid_status"),
}

_NON_DEFAULTABLE_SCALAR_KEYS = {"title", "creator"}


def _normalize_enum_option(value: str, options: list[Any]) -> Optional[str]:
    """Normalize an enum value using ordered ids or key names.

    Args:
        value: Raw value provided by the user.
        options: Ordered enum option keys.

    Returns:
        The normalized key, or None if the value is invalid.
    """
    raw = str(value).strip()
    if raw.isdigit():
        idx = int(raw)
        if 0 <= idx < len(options):
            return str(options[idx])

    lowered = raw.lower()
    for option in options:
        text = str(option)
        if text.lower() == lowered:
            return text
    return None


def _validate_set_value(
        repository: TaskRepository,
        real_prop: str,
        value: str,
) -> tuple[bool, Optional[str], Optional[str]]:
    """Validate and normalize a scalar field value.

    Args:
        repository: Repository backend.
        real_prop: Normalized property name.
        value: Raw value.

    Returns:
        A ``(success, normalized_value, error_key)`` tuple.
    """
    validator_spec = _ENUM_VALIDATORS.get(real_prop)
    if validator_spec:
        validator, err_key = validator_spec
        validated = validator(value)
        if not validated:
            return False, None, err_key
        return True, validated, None

    get_definition = getattr(repository, "get_field_definition", None)
    if not callable(get_definition):
        return True, value, None

    definition = get_definition(real_prop)
    if not definition:
        return True, value, None

    if str(definition.get("value_kind", "")).lower() != "enum":
        return True, value, None

    normalized = _normalize_enum_option(value, definition.get("enum_values", []))
    if normalized is None:
        return False, None, "sakuraflow.msg.invalid_enum_value"

    return True, normalized, None


def add_task(repository: TaskRepository, title: str, creator: str) -> str:
    """Create a task.

    Args:
        repository: Repository backend.
        title: Task title.
        creator: Task creator.

    Returns:
        The new task id as a string.
    """
    return repository.add_task(title, creator)


def update_status(repository: TaskRepository, task_id: str, status: Status, editor: str) -> bool:
    """Update a task status.

    Args:
        repository: Repository backend.
        task_id: Task id.
        status: New status.
        editor: Editor name.

    Returns:
        True if the update succeeded, otherwise False.
    """
    return repository.update_task(task_id, "status", status.value, editor)


def add_note(repository: TaskRepository, task_id: str, content: str, author: str) -> bool:
    """Add a note to a task.

    Args:
        repository: Repository backend.
        task_id: Task id.
        content: Note content.
        author: Note author.

    Returns:
        True if the note was added, otherwise False.
    """
    return repository.add_note(task_id, content, author)


def set_property(
        repository: TaskRepository,
        task_id: str,
        prop_alias: str,
        value: str,
        editor: str,
) -> tuple[bool, Any, Optional[str]]:
    """Set a scalar task property.

    Args:
        repository: Repository backend.
        task_id: Task id.
        prop_alias: Property name or alias.
        value: New value.
        editor: Editor name.

    Returns:
        A ``(success, processed_value, error_key)`` tuple.
    """
    real_prop = PROP_ALIASES.get(prop_alias.lower()) or prop_alias.strip()
    if not real_prop:
        return False, None, "sakuraflow.msg.invalid_prop_alias"

    valid, processed_val, err = _validate_set_value(repository, real_prop, value)
    if not valid:
        return False, None, err

    success = repository.update_task(task_id, real_prop, processed_val, editor)
    return success, processed_val, None


def append_list_property(
        repository: TaskRepository,
        task_id: str,
        list_alias: str,
        value: str,
        editor: str,
) -> tuple[bool, Optional[str], Optional[str]]:
    """Append a value to a list property.

    Args:
        repository: Repository backend.
        task_id: Task id.
        list_alias: List property name or alias.
        value: Value to append.
        editor: Editor name.

    Returns:
        A ``(success, error_key, detail)`` tuple.
    """
    real_prop = LIST_PROP_ALIASES.get(list_alias.lower()) or list_alias.strip()
    if not real_prop:
        return False, "sakuraflow.msg.invalid_list_alias", None

    if real_prop == "dependencies" and str(task_id) == str(value):
        return False, "sakuraflow.msg.self_dependency", f"{task_id}->{value}({task_id}->{task_id})"

    if real_prop == "dependencies" and not repository.task_exists(value):
        return False, "sakuraflow.msg.dep_not_found", None

    if real_prop == "dependencies":
        success, cycle_path = repository.append_dependency(task_id, value, editor)
        if not success and cycle_path:
            if str(task_id) == str(value):
                return False, "sakuraflow.msg.self_dependency", cycle_path
            return False, "sakuraflow.msg.circular_dependency", cycle_path
        return success, None, None

    success = repository.update_task(task_id, real_prop, value, editor)
    return success, None, None


def remove_list_property(
        repository: TaskRepository,
        task_id: str,
        list_alias: str,
        value: str,
        editor: str,
) -> tuple[bool, Optional[str]]:
    """Remove a value from a list property.

    Args:
        repository: Repository backend.
        task_id: Task id.
        list_alias: List property name or alias.
        value: Value to remove.
        editor: Editor name.

    Returns:
        A ``(success, error_key)`` tuple.
    """
    real_prop = LIST_PROP_ALIASES.get(list_alias.lower()) or list_alias.strip()
    if not real_prop:
        return False, "sakuraflow.msg.invalid_list_alias"

    success = repository.remove_item(task_id, real_prop, value, editor)
    return success, None


def set_default_tier(repository: TaskRepository, tier_val: str) -> bool:
    """Set the default tier through the generic field-default flow.

    Args:
        repository: Repository backend.
        tier_val: New default tier value.

    Returns:
        True if the update succeeded, otherwise False.
    """
    warnings.warn(
        "set_default_tier is deprecated; configure defaults via field definitions instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    success, _value, _err = set_field_default(repository, "tier", tier_val)
    return success


def set_field_default(
        repository: TaskRepository,
        key_name: str,
        default_value: str,
) -> tuple[bool, Any, Optional[str]]:
    """Set a field default value.

    Args:
        repository: Repository backend.
        key_name: Field key.
        default_value: New default value.

    Returns:
        A ``(success, normalized_value, error_key)`` tuple.
    """
    key = str(key_name).strip().lower()
    if not key:
        return False, None, "invalid_field_key"

    if key in _NON_DEFAULTABLE_SCALAR_KEYS:
        return False, None, "default_not_allowed"

    definition = repository.get_field_definition(key)
    if not definition:
        return False, None, "field_not_found"

    if bool(definition.get("is_required", False)):
        return False, None, "default_not_allowed"

    value_kind = str(definition.get("value_kind", "")).lower()
    if value_kind == "list":
        return False, None, "default_not_allowed"

    normalized_default = str(default_value)
    if value_kind == "enum":
        normalized = _normalize_enum_option(normalized_default, definition.get("enum_values", []))
        if normalized is None:
            return False, None, "invalid_enum_default_value"
        normalized_default = normalized

    success = repository.set_field_default(key, normalized_default)
    if not success:
        return False, None, "persist_failed"

    return True, normalized_default, None

