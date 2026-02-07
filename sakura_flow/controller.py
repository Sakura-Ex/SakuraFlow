import time
from typing import Optional, Dict, Any

from .constants import PROP_ALIASES, LIST_PROP_ALIASES
from .enums import Status, Tier, Priority
from .manager import TodoManager


class SearchCache:
    def __init__(self, ttl: int = 300):
        self.cache = {}
        self.ttl = ttl  # Time to live in seconds

    def set(self, key: str, query: str, results: Dict[str, Any]):
        self.cache[key] = {
            'query': query,
            'results': results,
            'timestamp': time.time()
        }

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        entry = self.cache.get(key)
        if not entry:
            return None
        
        if time.time() - entry['timestamp'] > self.ttl:
            del self.cache[key]
            return None
            
        return entry

class TodoController:
    def __init__(self, manager: TodoManager):
        self.manager = manager
        self.search_cache = SearchCache()

    def add_task(self, title: str, creator: str) -> str:
        return self.manager.add_task(title, creator)

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self.manager.data["tasks"].get(task_id)

    # Deprecated: Use search_tasks({'status': '!Done'}) instead
    def get_tasks(self, include_done: bool = False) -> Dict[str, Dict[str, Any]]:
        if include_done:
            return self.manager.data["tasks"]
        return self.search_tasks({'status': '!Done'})

    # Deprecated: Use search_tasks({'status': 'Done'}) instead
    def get_archived_tasks(self) -> Dict[str, Dict[str, Any]]:
        return self.search_tasks({'status': 'Done'})

    def search_tasks(self, criteria: Dict[str, str], cache_key: str = None) -> Dict[str, Dict[str, Any]]:
        """
        根据条件搜索任务
        criteria: {
            'title': 'keyword',
            'status': 'In Progress' or '!Done',
            'tier': 'IV' or '!IV',
            'priority': 'High' or '!High',
            'creator': 'player_name' or '!player_name',
            'collaborator': 'player_name' or '!player_name',
            'label': 'tag' or '!tag'
        }
        """
        result = {}
        for tid, task in self.manager.data["tasks"].items():
            match = True
            
            # Title (Fuzzy)
            if 'title' in criteria and criteria['title'].lower() not in task['title'].lower():
                match = False
            
            # Helper for exact match with negation
            def check_exact(field_val, target_val):
                if target_val.startswith('!'):
                    return field_val.lower() != target_val[1:].lower()
                return field_val.lower() == target_val.lower()

            # Helper for list contains with negation
            def check_contains(field_list, target_val):
                field_list_lower = [x.lower() for x in field_list]
                if target_val.startswith('!'):
                    return target_val[1:].lower() not in field_list_lower
                return target_val.lower() in field_list_lower

            # Status
            if match and 'status' in criteria:
                if not check_exact(task['status'], criteria['status']):
                    match = False

            # Tier
            if match and 'tier' in criteria:
                if not check_exact(task.get('tier', ''), criteria['tier']):
                    match = False

            # Priority
            if match and 'priority' in criteria:
                if not check_exact(task.get('priority', ''), criteria['priority']):
                    match = False

            # Creator
            if match and 'creator' in criteria:
                if not check_exact(task.get('creator', ''), criteria['creator']):
                    match = False

            # Collaborator
            if match and 'collaborator' in criteria:
                if not check_contains(task.get('collaborators', []), criteria['collaborator']):
                    match = False

            # Label
            if match and 'label' in criteria:
                if not check_contains(task.get('labels', []), criteria['label']):
                    match = False

            if match:
                result[tid] = task
        
        # Update cache if key provided
        if cache_key:
            # Construct a query string representation for cache (optional, mainly for debug/UI)
            query_str = " ".join([f"{k}={v}" for k, v in criteria.items()])
            self.search_cache.set(cache_key, query_str, result)

        return result

    def get_cached_search(self, cache_key: str) -> Optional[Dict[str, Any]]:
        entry = self.search_cache.get(cache_key)
        return entry['results'] if entry else None

    def update_status(self, task_id: str, status: Status, editor: str) -> bool:
        return self.manager.update_task(task_id, "status", status.value, editor)

    def add_note(self, task_id: str, content: str, author: str) -> bool:
        return self.manager.add_note(task_id, content, author)

    def set_property(self, task_id: str, prop_alias: str, value: str, editor: str) -> tuple[bool, Any, Optional[str]]:
        """
        设置属性
        Returns: (success, processed_value, error_key)
        """
        real_prop = PROP_ALIASES.get(prop_alias.lower())
        if not real_prop:
            return False, None, 'sakuraflow.msg.invalid_prop_alias'

        processed_val = value

        if real_prop == "tier":
            validated = Tier.validate(value)
            if not validated:
                return False, None, 'sakuraflow.msg.invalid_tier'
            processed_val = validated

        elif real_prop == "priority":
            validated = Priority.validate(value)
            if not validated:
                return False, None, 'sakuraflow.msg.invalid_priority'
            processed_val = validated

        elif real_prop == "status":
            validated = Status.validate(value)
            if not validated:
                return False, None, 'sakuraflow.msg.invalid_status'
            processed_val = validated

        success = self.manager.update_task(task_id, real_prop, processed_val, editor)
        return success, processed_val, None

    def append_list_property(self, task_id: str, list_alias: str, value: str, editor: str) -> tuple[bool, Optional[str]]:
        """
        追加列表属性
        Returns: (success, error_key)
        """
        real_prop = LIST_PROP_ALIASES.get(list_alias.lower())
        if not real_prop:
            return False, 'sakuraflow.msg.invalid_list_alias'

        if real_prop == "dependencies" and value not in self.manager.data["tasks"]:
            return False, 'sakuraflow.msg.dep_not_found'

        success = self.manager.update_task(task_id, real_prop, value, editor)
        return success, None

    def remove_list_property(self, task_id: str, list_alias: str, value: str, editor: str) -> tuple[bool, Optional[str]]:
        """
        移除列表属性
        Returns: (success, error_key)
        """
        real_prop = LIST_PROP_ALIASES.get(list_alias.lower())
        if not real_prop:
            return False, 'sakuraflow.msg.invalid_list_alias'

        success = self.manager.remove_item(task_id, real_prop, value, editor)
        return success, None

    def set_default_tier(self, tier_val: str) -> bool:
        validated = Tier.validate(tier_val)
        if validated:
            self.manager.set_default_tier(validated)
            return True
        return False
