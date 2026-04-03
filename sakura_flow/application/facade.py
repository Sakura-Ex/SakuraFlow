import warnings
from typing import Dict, Optional

from .search_cache import SearchCache
from .use_cases import task_mutations, task_queries
from ..enums import Status
from ..ports.repository import TaskRepository


class TodoApplication:
    """Application facade used by frontend adapters (MCDR/CLI)."""

    def __init__(self, repository: TaskRepository):
        """Create the facade with a repository backend.

        Args:
            repository: Repository implementation used for persistence.
        """
        self.repository = repository
        self.search_cache = SearchCache()

    def add_task(self, title: str, creator: str) -> str:
        """Create a new task.

        Args:
            title: Task title.
            creator: Task creator.

        Returns:
            The new task id as a string.
        """
        return task_mutations.add_task(self.repository, title, creator)

    def get_task(self, task_id: str):
        """Fetch a single task by id."""
        return task_queries.get_task(self.repository, task_id)

    def get_tasks(self, include_done: bool = False):
        """Fetch tasks, optionally including completed ones.

        Args:
            include_done: Whether to include completed tasks.

        Returns:
            A mapping of task id to task objects.
        """
        return task_queries.get_tasks(self.repository, include_done=include_done)

    def get_archived_tasks(self):
        """Fetch archived tasks."""
        return task_queries.get_archived_tasks(self.repository)

    def search_tasks(self, criteria: Dict[str, str], cache_key: str = None):
        """Search tasks and optionally cache the result.

        Args:
            criteria: Search criteria dictionary.
            cache_key: Optional cache key used for paging reuse.

        Returns:
            A mapping of task id to matching task objects.
        """
        return task_queries.search_tasks(
            self.repository,
            criteria,
            cache=self.search_cache,
            cache_key=cache_key,
        )

    def get_cached_search(self, cache_key: str) -> Optional[Dict[str, dict]]:
        """Return a cached search result if it is still valid."""
        return task_queries.get_cached_search(self.search_cache, cache_key)

    def update_status(self, task_id: str, status: Status, editor: str) -> bool:
        """Update the status of a task.

        Args:
            task_id: Task id to update.
            status: New status value.
            editor: Editor name.

        Returns:
            True if the update succeeded, otherwise False.
        """
        return task_mutations.update_status(self.repository, task_id, status, editor)

    def add_note(self, task_id: str, content: str, author: str) -> bool:
        """Append a note to a task.

        Args:
            task_id: Task id to update.
            content: Note content.
            author: Note author.

        Returns:
            True if the note was added, otherwise False.
        """
        return task_mutations.add_note(self.repository, task_id, content, author)

    def set_property(self, task_id: str, prop_alias: str, value: str, editor: str):
        """Set a scalar task property.

        Args:
            task_id: Task id to update.
            prop_alias: Property name or alias.
            value: New value.
            editor: Editor name.

        Returns:
            A ``(success, processed_value, error_key)`` tuple.
        """
        return task_mutations.set_property(self.repository, task_id, prop_alias, value, editor)

    def append_list_property(self, task_id: str, list_alias: str, value: str, editor: str):
        """Append a value to a list property.

        Args:
            task_id: Task id to update.
            list_alias: List property name or alias.
            value: Value to append.
            editor: Editor name.

        Returns:
            A ``(success, error_key, detail)`` tuple.
        """
        return task_mutations.append_list_property(self.repository, task_id, list_alias, value, editor)

    def remove_list_property(self, task_id: str, list_alias: str, value: str, editor: str):
        """Remove a value from a list property.

        Args:
            task_id: Task id to update.
            list_alias: List property name or alias.
            value: Value to remove.
            editor: Editor name.

        Returns:
            A ``(success, error_key)`` tuple.
        """
        return task_mutations.remove_list_property(self.repository, task_id, list_alias, value, editor)

    def set_default_tier(self, tier_val: str) -> bool:
        """Set the default tier value.

        Args:
            tier_val: New default tier value.

        Returns:
            True if the default was updated, otherwise False.
        """
        warnings.warn(
            "TodoApplication.set_default_tier is deprecated; use field-definition defaults.",
            DeprecationWarning,
            stacklevel=2,
        )
        return task_mutations.set_default_tier(self.repository, tier_val)

    def get_field_definition(self, key_name: str):
        """Fetch a field definition by key name.

        Args:
            key_name: Field key.

        Returns:
            A field-definition dictionary or None.
        """
        return task_queries.get_field_definition(self.repository, key_name)

    def set_field_default(self, key_name: str, default_value: str):
        """Set the default value for a field definition.

        Args:
            key_name: Field key.
            default_value: New default value.

        Returns:
            A ``(success, normalized_value, error_key)`` tuple.
        """
        return task_mutations.set_field_default(self.repository, key_name, default_value)

