import warnings
from typing import Any, Optional

from ...constants import LIST_PROP_ALIASES, PROP_ALIASES
from ...enums import Priority, Status, Tier
from ...ports.repository import TaskRepository


def add_task(repository: TaskRepository, title: str, creator: str) -> str:
    return repository.add_task(title, creator)


def update_status(repository: TaskRepository, task_id: str, status: Status, editor: str) -> bool:
    return repository.update_task(task_id, "status", status.value, editor)


def add_note(repository: TaskRepository, task_id: str, content: str, author: str) -> bool:
    return repository.add_note(task_id, content, author)


def set_property(
        repository: TaskRepository,
        task_id: str,
        prop_alias: str,
        value: str,
        editor: str,
) -> tuple[bool, Any, Optional[str]]:
    real_prop = PROP_ALIASES.get(prop_alias.lower()) or prop_alias.strip()
    if not real_prop:
        return False, None, "sakuraflow.msg.invalid_prop_alias"

    processed_val = value
    if real_prop == "tier":
        validated = Tier.validate(value)
        if not validated:
            return False, None, "sakuraflow.msg.invalid_tier"
        processed_val = validated
    elif real_prop == "priority":
        validated = Priority.validate(value)
        if not validated:
            return False, None, "sakuraflow.msg.invalid_priority"
        processed_val = validated
    elif real_prop == "status":
        validated = Status.validate(value)
        if not validated:
            return False, None, "sakuraflow.msg.invalid_status"
        processed_val = validated

    success = repository.update_task(task_id, real_prop, processed_val, editor)
    return success, processed_val, None


def append_list_property(
        repository: TaskRepository,
        task_id: str,
        list_alias: str,
        value: str,
        editor: str,
) -> tuple[bool, Optional[str], Optional[str]]:
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
    real_prop = LIST_PROP_ALIASES.get(list_alias.lower()) or list_alias.strip()
    if not real_prop:
        return False, "sakuraflow.msg.invalid_list_alias"

    success = repository.remove_item(task_id, real_prop, value, editor)
    return success, None


def set_default_tier(repository: TaskRepository, tier_val: str) -> bool:
    warnings.warn(
        "set_default_tier is deprecated; configure defaults via field definitions instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    validated = Tier.validate(tier_val)
    if validated:
        repository.set_default_tier(validated)
        return True
    return False
