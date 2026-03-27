from typing import Dict, Optional

from ..search_cache import SearchCache
from ...ports.repository import TaskRepository


def get_task(repository: TaskRepository, task_id: str):
    return repository.get_task(task_id)


def get_tasks(repository: TaskRepository, include_done: bool = False):
    if include_done:
        return repository.get_all_tasks()
    return search_tasks(repository, {"status": "!Done"})


def get_archived_tasks(repository: TaskRepository):
    return search_tasks(repository, {"status": "Done"})


def search_tasks(
        repository: TaskRepository,
        criteria: Dict[str, str],
        cache: Optional[SearchCache] = None,
        cache_key: str = None,
):
    result = repository.search_tasks(criteria)
    if cache and cache_key:
        query_str = " ".join([f"{k}={v}" for k, v in criteria.items()])
        cache.set(cache_key, query_str, result)
    return result


def get_cached_search(cache: SearchCache, cache_key: str):
    entry = cache.get(cache_key)
    return entry["results"] if entry else None
