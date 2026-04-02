from typing import Any, Dict, Optional, Protocol


class TaskRepository(Protocol):
    def add_task(self, title: str, creator: str) -> str:
        ...

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        ...

    def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        ...

    def search_tasks(self, criteria: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
        ...

    def task_exists(self, task_id: str) -> bool:
        ...

    def update_task(self, task_id: str, key: str, value: Any, editor: str) -> bool:
        ...

    def append_dependency(self, task_id: str, dependency_id: str, editor: str) -> tuple[bool, Optional[str]]:
        """Append a dependency edge and return (success, cycle_path_if_any)."""
        ...

    def remove_item(self, task_id: str, key: str, value: str, editor: str) -> bool:
        ...

    def add_note(self, task_id: str, content: str, author: str) -> bool:
        ...

    def set_default_tier(self, tier: str):
        # Deprecated: use field definition defaults (e.g. upsert_field_definition) instead.
        ...
