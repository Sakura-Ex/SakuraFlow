from typing import Dict, Optional

from .search_cache import SearchCache
from .use_cases import task_mutations, task_queries
from ..enums import Status
from ..ports.repository import TaskRepository


class TodoApplication:
    """Application facade used by frontend adapters (MCDR/CLI)."""

    def __init__(self, repository: TaskRepository):
        self.repository = repository
        self.search_cache = SearchCache()

    def add_task(self, title: str, creator: str) -> str:
        return task_mutations.add_task(self.repository, title, creator)

    def get_task(self, task_id: str):
        return task_queries.get_task(self.repository, task_id)

    def get_tasks(self, include_done: bool = False):
        return task_queries.get_tasks(self.repository, include_done=include_done)

    def get_archived_tasks(self):
        return task_queries.get_archived_tasks(self.repository)

    def search_tasks(self, criteria: Dict[str, str], cache_key: str = None):
        return task_queries.search_tasks(
            self.repository,
            criteria,
            cache=self.search_cache,
            cache_key=cache_key,
        )

    def get_cached_search(self, cache_key: str) -> Optional[Dict[str, dict]]:
        return task_queries.get_cached_search(self.search_cache, cache_key)

    def update_status(self, task_id: str, status: Status, editor: str) -> bool:
        return task_mutations.update_status(self.repository, task_id, status, editor)

    def add_note(self, task_id: str, content: str, author: str) -> bool:
        return task_mutations.add_note(self.repository, task_id, content, author)

    def set_property(self, task_id: str, prop_alias: str, value: str, editor: str):
        return task_mutations.set_property(self.repository, task_id, prop_alias, value, editor)

    def append_list_property(self, task_id: str, list_alias: str, value: str, editor: str):
        return task_mutations.append_list_property(self.repository, task_id, list_alias, value, editor)

    def remove_list_property(self, task_id: str, list_alias: str, value: str, editor: str):
        return task_mutations.remove_list_property(self.repository, task_id, list_alias, value, editor)

    def set_default_tier(self, tier_val: str) -> bool:
        return task_mutations.set_default_tier(self.repository, tier_val)
