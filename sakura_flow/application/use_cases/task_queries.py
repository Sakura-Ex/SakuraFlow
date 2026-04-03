from typing import Dict, Optional

from ..search_cache import SearchCache
from ...ports.repository import TaskRepository


def get_task(repository: TaskRepository, task_id: str):
    """Fetch a single task.

    Args:
        repository: Repository backend.
        task_id: Task id to fetch.

    Returns:
        The task object, or None if not found.
    """
    return repository.get_task(task_id)


def get_tasks(repository: TaskRepository, include_done: bool = False):
    """Fetch active tasks or all tasks.

    Args:
        repository: Repository backend.
        include_done: Whether to include completed tasks.

    Returns:
        A mapping of task id to task objects.
    """
    if include_done:
        return repository.get_all_tasks()
    return search_tasks(repository, {"status": "!Done"})


def get_archived_tasks(repository: TaskRepository):
    """Fetch archived tasks.

    Args:
        repository: Repository backend.

    Returns:
        A mapping of task id to archived task objects.
    """
    return search_tasks(repository, {"status": "Done"})


def search_tasks(
        repository: TaskRepository,
        criteria: Dict[str, str],
        cache: Optional[SearchCache] = None,
        cache_key: str = None,
):
    """Search tasks and optionally store the result in a cache.

    Args:
        repository: Repository backend.
        criteria: Search criteria dictionary.
        cache: Optional search cache instance.
        cache_key: Optional cache key.

    Returns:
        A mapping of task id to matching task objects.
    """
    result = repository.search_tasks(criteria)
    if cache and cache_key:
        query_str = " ".join([f"{k}={v}" for k, v in criteria.items()])
        cache.set(cache_key, query_str, result)
    return result


def get_cached_search(cache: SearchCache, cache_key: str):
    """Return a cached search result.

    Args:
        cache: Search cache instance.
        cache_key: Cache key.

    Returns:
        Cached search results, or None if unavailable.
    """
    entry = cache.get(cache_key)
    return entry["results"] if entry else None


def get_field_definition(repository: TaskRepository, key_name: str):
    """Fetch a field definition from the repository.

    Args:
        repository: Repository backend.
        key_name: Field key.

    Returns:
        A field-definition dictionary or None.
    """
    return repository.get_field_definition(key_name)
