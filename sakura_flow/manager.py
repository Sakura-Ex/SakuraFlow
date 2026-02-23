import json
import os
import time
from typing import Dict, Any, List
from contextlib import contextmanager
from .enums import Status


class FileLock:
    """简单的基于文件的互斥锁"""
    def __init__(self, lock_file: str, timeout: int = 5, delay: float = 0.1):
        self.lock_file = lock_file
        self.timeout = timeout
        self.delay = delay

    def acquire(self):
        start_time = time.time()
        while True:
            try:
                # 确保锁文件的父目录存在
                os.makedirs(os.path.dirname(self.lock_file), exist_ok=True)
                # 尝试以独占模式创建锁文件
                fd = os.open(self.lock_file, os.O_CREAT | os.O_EXCL | os.O_RDWR)
                os.close(fd)
                return True
            except OSError:
                # 文件已存在，说明被锁定
                if time.time() - start_time >= self.timeout:
                    raise TimeoutError(f"Could not acquire lock on {self.lock_file}")
                time.sleep(self.delay)

    def release(self):
        try:
            os.remove(self.lock_file)
        except OSError:
            pass

    @contextmanager
    def lock(self):
        self.acquire()
        try:
            yield
        finally:
            self.release()


class TodoManager:
    def __init__(self, data_path: str):
        self.data_path = data_path
        self.lock_path = data_path + ".lock"
        self.file_lock = FileLock(self.lock_path)
        self.data: Dict[str, Any] = {"tasks": {}, "next_id": 1, "default_tier": "LV"}
        # 初始加载不需要锁，因为只是读取
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

    @contextmanager
    def transaction(self):
        """
        事务上下文：获取锁 -> 重新加载数据 -> 执行操作 -> 保存数据 -> 释放锁
        """
        with self.file_lock.lock():
            self.load()  # 关键：在持有锁的情况下重新加载最新数据
            yield
            self.save()

    def set_default_tier(self, tier: str):
        with self.transaction():
            self.data["default_tier"] = tier

    def add_task(self, title: str, creator: str) -> str:
        with self.transaction():
            task_id = str(self.data["next_id"])
            self.data["tasks"][task_id] = {
                "title": title,
                "creator": creator,
                "description": "",
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
        with self.transaction():
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
            return True

    def remove_item(self, task_id: str, key: str, value: str, editor: str) -> bool:
        with self.transaction():
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
                return True
            return False

    def add_note(self, task_id: str, content: str, author: str) -> bool:
        with self.transaction():
            task = self.data["tasks"].get(task_id)
            if not task: return False
            note = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "author": author, "content": content}
            task["notes"].append(note)
            task.update({"last_updated": note["time"], "last_editor": author})
            return True
