import json
import os
import shutil
import sqlite3
import time
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

from .enums import Status


class TodoManager:
    def __init__(self, db_path: str, legacy_json_path: Optional[str] = None):
        self.db_path = db_path
        self.legacy_json_path = legacy_json_path
        self.startup_warning: Optional[str] = None
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self._init_db()
        self._ensure_default_tier_row()
        self._auto_migrate_legacy_json_if_needed()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS meta
                (
                    key   TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS tasks
                (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    title        TEXT NOT NULL,
                    creator      TEXT NOT NULL,
                    description  TEXT NOT NULL DEFAULT '',
                    status       TEXT NOT NULL,
                    tier         TEXT NOT NULL,
                    priority     TEXT NOT NULL,
                    created_at   TEXT NOT NULL,
                    last_updated TEXT NOT NULL,
                    last_editor  TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS task_collaborators
                (
                    task_id      INTEGER NOT NULL,
                    collaborator TEXT    NOT NULL,
                    PRIMARY KEY (task_id, collaborator),
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS task_labels
                (
                    task_id INTEGER NOT NULL,
                    label   TEXT    NOT NULL,
                    PRIMARY KEY (task_id, label),
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS task_dependencies
                (
                    task_id       INTEGER NOT NULL,
                    dependency_id INTEGER NOT NULL,
                    PRIMARY KEY (task_id, dependency_id),
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
                    FOREIGN KEY (dependency_id) REFERENCES tasks (id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS task_notes
                (
                    id      INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    time    TEXT    NOT NULL,
                    author  TEXT    NOT NULL,
                    content TEXT    NOT NULL,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks (status);
                CREATE INDEX IF NOT EXISTS idx_tasks_tier ON tasks (tier);
                CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks (priority);
                CREATE INDEX IF NOT EXISTS idx_tasks_creator ON tasks (creator);
                CREATE INDEX IF NOT EXISTS idx_collaborators_name ON task_collaborators (collaborator);
                CREATE INDEX IF NOT EXISTS idx_labels_name ON task_labels (label);
                CREATE INDEX IF NOT EXISTS idx_dependencies_dep_id ON task_dependencies (dependency_id);
                """
            )

    def _ensure_default_tier_row(self):
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO meta(key, value) VALUES('default_tier', 'LV')"
            )

    def _is_empty_db(self) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS cnt FROM tasks").fetchone()
            return int(row["cnt"]) == 0

    def _auto_migrate_legacy_json_if_needed(self):
        if not self.legacy_json_path:
            return
        if not os.path.exists(self.legacy_json_path):
            return
        if not self._is_empty_db():
            return

        try:
            self._migrate_from_json(self.legacy_json_path)
            backup_path = self.legacy_json_path + ".bak"
            if not os.path.exists(backup_path):
                shutil.copy2(self.legacy_json_path, backup_path)
        except Exception as exc:  # noqa: BLE001
            self.startup_warning = (
                f"Sakura Flow migration failed, started with empty SQLite DB: {exc}"
            )

    def _migrate_from_json(self, json_path: str):
        with open(json_path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        tasks = payload.get("tasks", {})
        default_tier = payload.get("default_tier", "LV")

        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("UPDATE meta SET value = ? WHERE key = 'default_tier'", (default_tier,))

            max_task_id = 0
            inserted_task_ids = set()
            pending_dependencies = []
            for tid, task in tasks.items():
                if not str(tid).isdigit() or not isinstance(task, dict):
                    continue
                task_id = int(tid)
                max_task_id = max(max_task_id, task_id)
                inserted_task_ids.add(task_id)

                conn.execute(
                    """
                    INSERT OR REPLACE INTO tasks(
                        id, title, creator, description, status, tier, priority,
                        created_at, last_updated, last_editor
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task_id,
                        task.get("title", ""),
                        task.get("creator", ""),
                        task.get("description", ""),
                        task.get("status", Status.IN_PROGRESS.value),
                        task.get("tier", default_tier),
                        task.get("priority", "Medium"),
                        task.get("created_at", time.strftime("%Y-%m-%d %H:%M:%S")),
                        task.get("last_updated", time.strftime("%Y-%m-%d %H:%M:%S")),
                        task.get("last_editor", task.get("creator", "System")),
                    ),
                )

                for collaborator in sorted(set(task.get("collaborators", []))):
                    conn.execute(
                        "INSERT OR IGNORE INTO task_collaborators(task_id, collaborator) VALUES (?, ?)",
                        (task_id, collaborator),
                    )
                for label in sorted(set(task.get("labels", []))):
                    conn.execute(
                        "INSERT OR IGNORE INTO task_labels(task_id, label) VALUES (?, ?)",
                        (task_id, label),
                    )
                for dep in task.get("dependencies", []):
                    if not str(dep).isdigit():
                        continue
                    pending_dependencies.append((task_id, int(dep)))
                for note in task.get("notes", []):
                    if not isinstance(note, dict):
                        continue
                    conn.execute(
                        "INSERT INTO task_notes(task_id, time, author, content) VALUES (?, ?, ?, ?)",
                        (
                            task_id,
                            note.get("time", time.strftime("%Y-%m-%d %H:%M:%S")),
                            note.get("author", "System"),
                            note.get("content", ""),
                        ),
                    )

            for task_id, dep_id in sorted(set(pending_dependencies)):
                if dep_id not in inserted_task_ids:
                    continue
                conn.execute(
                    "INSERT OR IGNORE INTO task_dependencies(task_id, dependency_id) VALUES (?, ?)",
                    (task_id, dep_id),
                )

            if max_task_id > 0:
                conn.execute(
                    "INSERT OR REPLACE INTO sqlite_sequence(name, seq) VALUES('tasks', ?)",
                    (max_task_id,),
                )

            conn.commit()

    @contextmanager
    def transaction(self):
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _default_tier(self, conn: sqlite3.Connection) -> str:
        row = conn.execute("SELECT value FROM meta WHERE key = 'default_tier'").fetchone()
        return row["value"] if row else "LV"

    def _fetch_list_map(
            self,
            conn: sqlite3.Connection,
            table: str,
            key_field: str,
            task_ids: Optional[List[int]] = None,
    ) -> Dict[str, List[str]]:
        if task_ids is None:
            rows = conn.execute(f"SELECT task_id, {key_field} AS val FROM {table}").fetchall()
        elif not task_ids:
            rows = []
        else:
            placeholders = ",".join(["?"] * len(task_ids))
            rows = conn.execute(
                f"SELECT task_id, {key_field} AS val FROM {table} WHERE task_id IN ({placeholders})",
                task_ids,
            ).fetchall()
        result: Dict[str, List[str]] = {}
        for row in rows:
            tid = str(row["task_id"])
            result.setdefault(tid, []).append(str(row["val"]))
        return result

    def _fetch_notes_map(self, conn: sqlite3.Connection, task_ids: Optional[List[int]] = None) -> Dict[
        str, List[Dict[str, str]]]:
        if task_ids is None:
            rows = conn.execute(
                "SELECT task_id, time, author, content FROM task_notes ORDER BY id ASC"
            ).fetchall()
        elif not task_ids:
            rows = []
        else:
            placeholders = ",".join(["?"] * len(task_ids))
            rows = conn.execute(
                f"SELECT task_id, time, author, content FROM task_notes WHERE task_id IN ({placeholders}) ORDER BY id ASC",
                task_ids,
            ).fetchall()
        result: Dict[str, List[Dict[str, str]]] = {}
        for row in rows:
            tid = str(row["task_id"])
            result.setdefault(tid, []).append(
                {
                    "time": row["time"],
                    "author": row["author"],
                    "content": row["content"],
                }
            )
        return result

    def _assemble_tasks_from_rows(self, conn: sqlite3.Connection, task_rows: List[sqlite3.Row]) -> Dict[
        str, Dict[str, Any]]:
        task_ids = [int(row["id"]) for row in task_rows]
        collaborators = self._fetch_list_map(conn, "task_collaborators", "collaborator", task_ids)
        labels = self._fetch_list_map(conn, "task_labels", "label", task_ids)
        deps = self._fetch_list_map(conn, "task_dependencies", "dependency_id", task_ids)
        notes = self._fetch_notes_map(conn, task_ids)

        result: Dict[str, Dict[str, Any]] = {}
        for row in task_rows:
            tid = str(row["id"])
            dep_list = deps.get(tid, [])
            dep_list.sort(key=lambda x: int(x) if str(x).isdigit() else str(x))
            collab_list = sorted(collaborators.get(tid, []))
            label_list = sorted(labels.get(tid, []))

            result[tid] = {
                "title": row["title"],
                "creator": row["creator"],
                "description": row["description"],
                "status": row["status"],
                "tier": row["tier"],
                "priority": row["priority"],
                "labels": label_list,
                "collaborators": collab_list,
                "dependencies": dep_list,
                "notes": notes.get(tid, []),
                "created_at": row["created_at"],
                "last_updated": row["last_updated"],
                "last_editor": row["last_editor"],
            }
        return result

    def _get_tasks_by_ids(self, conn: sqlite3.Connection, task_ids: List[int]) -> Dict[str, Dict[str, Any]]:
        if not task_ids:
            return {}
        placeholders = ",".join(["?"] * len(task_ids))
        rows = conn.execute(
            f"SELECT * FROM tasks WHERE id IN ({placeholders}) ORDER BY id ASC",
            task_ids,
        ).fetchall()
        return self._assemble_tasks_from_rows(conn, rows)

    def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        with self._connect() as conn:
            task_rows = conn.execute("SELECT * FROM tasks ORDER BY id ASC").fetchall()
            return self._assemble_tasks_from_rows(conn, task_rows)

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        if not str(task_id).isdigit():
            return None
        with self._connect() as conn:
            tasks = self._get_tasks_by_ids(conn, [int(task_id)])
            return tasks.get(str(task_id))

    @staticmethod
    def _escape_like_fragment(raw: str) -> str:
        return raw.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    def search_tasks(self, criteria: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
        where_clauses: List[str] = []
        params: List[Any] = []

        title_val = criteria.get("title")
        if title_val is not None:
            escaped = self._escape_like_fragment(title_val)
            where_clauses.append("LOWER(t.title) LIKE LOWER(?) ESCAPE '\\'")
            params.append(f"%{escaped}%")

        for key in ["status", "tier", "priority", "creator"]:
            val = criteria.get(key)
            if val is None:
                continue
            neg = val.startswith("!")
            target = val[1:] if neg else val
            if neg:
                where_clauses.append(f"LOWER(t.{key}) != LOWER(?)")
            else:
                where_clauses.append(f"LOWER(t.{key}) = LOWER(?)")
            params.append(target)

        for key, table, field in [
            ("collaborator", "task_collaborators", "collaborator"),
            ("label", "task_labels", "label"),
        ]:
            val = criteria.get(key)
            if val is None:
                continue
            neg = val.startswith("!")
            target = val[1:] if neg else val
            base = (
                f"SELECT 1 FROM {table} x "
                f"WHERE x.task_id = t.id AND LOWER(x.{field}) = LOWER(?)"
            )
            where_clauses.append(f"NOT EXISTS ({base})" if neg else f"EXISTS ({base})")
            params.append(target)

        sql = "SELECT t.id FROM tasks t"
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        sql += " ORDER BY t.id ASC"

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            task_ids = [int(row["id"]) for row in rows]
            return self._get_tasks_by_ids(conn, task_ids)

    def task_exists(self, task_id: str) -> bool:
        if not str(task_id).isdigit():
            return False
        with self._connect() as conn:
            row = conn.execute("SELECT 1 FROM tasks WHERE id = ?", (int(task_id),)).fetchone()
            return row is not None

    @property
    def data(self) -> Dict[str, Any]:
        tasks = self.get_all_tasks()
        with self._connect() as conn:
            default_tier = self._default_tier(conn)
            row = conn.execute("SELECT COALESCE(MAX(id), 0) AS max_id FROM tasks").fetchone()
            next_id = int(row["max_id"]) + 1
        return {"tasks": tasks, "next_id": next_id, "default_tier": default_tier}

    def set_default_tier(self, tier: str):
        with self.transaction() as conn:
            conn.execute("UPDATE meta SET value = ? WHERE key = 'default_tier'", (tier,))

    def add_task(self, title: str, creator: str) -> str:
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        with self.transaction() as conn:
            tier = self._default_tier(conn)
            cursor = conn.execute(
                """
                INSERT INTO tasks(title, creator, description, status, tier, priority,
                                  created_at, last_updated, last_editor)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    title,
                    creator,
                    "",
                    Status.IN_PROGRESS.value,
                    tier,
                    "Medium",
                    now,
                    now,
                    creator,
                ),
            )
            return str(cursor.lastrowid)

    @staticmethod
    def _sort_collection(collection: List, key_type: str):
        if key_type == "dependencies":
            collection.sort(key=lambda x: int(x) if str(x).isdigit() else str(x))
        else:
            collection.sort()

    def update_task(self, task_id: str, key: str, value: Any, editor: str) -> bool:
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        with self.transaction() as conn:
            tid = int(task_id)
            task_row = conn.execute("SELECT 1 FROM tasks WHERE id = ?", (tid,)).fetchone()
            if not task_row:
                return False

            if key == "collaborators":
                cursor = conn.execute(
                    "INSERT OR IGNORE INTO task_collaborators(task_id, collaborator) VALUES (?, ?)",
                    (tid, str(value)),
                )
                if cursor.rowcount == 0:
                    return False
            elif key == "labels":
                cursor = conn.execute(
                    "INSERT OR IGNORE INTO task_labels(task_id, label) VALUES (?, ?)",
                    (tid, str(value)),
                )
                if cursor.rowcount == 0:
                    return False
            elif key == "dependencies":
                if not str(value).isdigit():
                    return False
                cursor = conn.execute(
                    "INSERT OR IGNORE INTO task_dependencies(task_id, dependency_id) VALUES (?, ?)",
                    (tid, int(value)),
                )
                if cursor.rowcount == 0:
                    return False
            else:
                if key not in {"title", "description", "status", "tier", "priority"}:
                    return False
                conn.execute(f"UPDATE tasks SET {key} = ? WHERE id = ?", (value, tid))

            conn.execute(
                "UPDATE tasks SET last_updated = ?, last_editor = ? WHERE id = ?",
                (now, editor, tid),
            )
            return True

    def remove_item(self, task_id: str, key: str, value: str, editor: str) -> bool:
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        with self.transaction() as conn:
            tid = int(task_id)
            task_row = conn.execute("SELECT 1 FROM tasks WHERE id = ?", (tid,)).fetchone()
            if not task_row or key not in ["collaborators", "dependencies", "labels"]:
                return False

            if key == "collaborators":
                cursor = conn.execute(
                    "DELETE FROM task_collaborators WHERE task_id = ? AND collaborator = ?",
                    (tid, value),
                )
            elif key == "labels":
                cursor = conn.execute(
                    "DELETE FROM task_labels WHERE task_id = ? AND label = ?",
                    (tid, value),
                )
            else:
                if not str(value).isdigit():
                    return False
                cursor = conn.execute(
                    "DELETE FROM task_dependencies WHERE task_id = ? AND dependency_id = ?",
                    (tid, int(value)),
                )

            if cursor.rowcount == 0:
                return False

            conn.execute(
                "UPDATE tasks SET last_updated = ?, last_editor = ? WHERE id = ?",
                (now, editor, tid),
            )
            return True

    def add_note(self, task_id: str, content: str, author: str) -> bool:
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        with self.transaction() as conn:
            tid = int(task_id)
            task_row = conn.execute("SELECT 1 FROM tasks WHERE id = ?", (tid,)).fetchone()
            if not task_row:
                return False

            conn.execute(
                "INSERT INTO task_notes(task_id, time, author, content) VALUES (?, ?, ?, ?)",
                (tid, now, author, content),
            )
            conn.execute(
                "UPDATE tasks SET last_updated = ?, last_editor = ? WHERE id = ?",
                (now, author, tid),
            )
            return True
