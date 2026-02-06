import json
import os
import time
from typing import Dict, Any, List
from .enums import Status


class TodoManager:
    def __init__(self, data_path: str):
        self.data_path = data_path
        self.data: Dict[str, Any] = {"tasks": {}, "next_id": 1, "default_tier": "LV"}
        self.load()

    def load(self):
        if os.path.exists(self.data_path):
            try:
                with open(self.data_path, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                    # 确保 default_tier 存在
                    if "default_tier" not in self.data:
                        self.data["default_tier"] = "LV"
            except (json.JSONDecodeError, IOError):
                self.data = {"tasks": {}, "next_id": 1, "default_tier": "LV"}

    def save(self):
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        try:
            with open(self.data_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except IOError:
            pass

    def set_default_tier(self, tier: str):
        self.data["default_tier"] = tier
        self.save()

    def add_task(self, title: str, creator: str) -> str:
        task_id = str(self.data["next_id"])
        self.data["tasks"][task_id] = {
            "title": title,
            "creator": creator,
            "description": "暂无描述", # TODO 移除硬编码
            "status": Status.IN_PROGRESS.value,
            "tier": self.data.get("default_tier", "LV"),
            "priority": "Medium",
            "labels": [],
            "collaborators": [],
            "dependencies": [],
            "notes": [],
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "last_editor": creator
        }
        self.data["next_id"] += 1
        self.save()
        return task_id

    @staticmethod
    def _sort_collection(collection: List, key_type: str):
        """
        模拟 TreeSet 的自然排序行为
        """
        if key_type == "dependencies":
            # 针对依赖 ID 进行数值自然排序 (确保 "2" < "10")
            collection.sort(key=lambda x: int(x) if str(x).isdigit() else str(x))
        else:
            # 针对协作人和标签进行字典序排序
            collection.sort()

    def update_task(self, task_id: str, key: str, value: Any, editor: str) -> bool:
        task = self.data["tasks"].get(task_id)
        if not task:
            return False

        # 列表属性去重与自然排序 (包含 labels)
        if key in ["collaborators", "dependencies", "labels"]:
            if value not in task[key]:
                task[key].append(value)
                self._sort_collection(task[key], key)
            else:
                return False
        else:
            task[key] = value

        task.update({
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "last_editor": editor
        })
        self.save()
        return True

    def remove_item(self, task_id: str, key: str, value: str, editor: str) -> bool:
        task = self.data["tasks"].get(task_id)
        # 确保 labels 也在可移除字段中
        if not task or key not in ["collaborators", "dependencies", "labels"]:
            return False

        if value in task[key]:
            task[key].remove(value)
            task.update({
                "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
                "last_editor": editor
            })
            self.save()
            return True
        return False

    def add_note(self, task_id: str, content: str, author: str) -> bool:
        task = self.data["tasks"].get(task_id)
        if not task: return False
        note = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "author": author, "content": content}
        task["notes"].append(note)
        task.update({"last_updated": note["time"], "last_editor": author})
        self.save()
        return True
