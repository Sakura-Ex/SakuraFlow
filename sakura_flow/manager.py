import json
import os
import shutil
import sqlite3
import time
import warnings
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple

from .enums import Priority, Status, Tier
from .ports.repository import TaskRepository

CORE_SCALAR_FIELDS = {"title", "description", "status", "tier", "priority"}
BUILTIN_LIST_FIELDS = {"collaborators", "labels"}


class TodoManager(TaskRepository):
    def __init__(self, db_path: str, legacy_json_path: Optional[str] = None):
        """Initialize the repository, database schema, field definitions, and migrations."""
        self.db_path = db_path
        self.legacy_json_path = legacy_json_path
        self.startup_warning: Optional[str] = None
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self._init_db()
        self._ensure_builtin_field_definitions()
        self._auto_migrate_legacy_json_if_needed()

    def _connect(self) -> sqlite3.Connection:
        """Create a SQLite connection with row factory and foreign keys enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self):
        """Create the base schema and indexes."""
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

                CREATE TABLE IF NOT EXISTS field_definitions
                (
                    key_name      TEXT PRIMARY KEY,
                    value_kind    TEXT    NOT NULL,
                    is_builtin    INTEGER NOT NULL DEFAULT 0,
                    is_required   INTEGER NOT NULL DEFAULT 0,
                    default_value TEXT,
                    enum_values   TEXT    NOT NULL DEFAULT '[]'
                );

                CREATE TABLE IF NOT EXISTS task_custom_values
                (
                    task_id    INTEGER NOT NULL,
                    key_name   TEXT    NOT NULL,
                    value_text TEXT    NOT NULL,
                    PRIMARY KEY (task_id, key_name),
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
                    FOREIGN KEY (key_name) REFERENCES field_definitions (key_name) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS task_list_items
                (
                    task_id    INTEGER NOT NULL,
                    prop_key   TEXT    NOT NULL,
                    prop_value TEXT    NOT NULL,
                    PRIMARY KEY (task_id, prop_key, prop_value),
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
                    time    TEXT NOT NULL,
                    author  TEXT NOT NULL,
                    content TEXT NOT NULL,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks (status);
                CREATE INDEX IF NOT EXISTS idx_tasks_tier ON tasks (tier);
                CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks (priority);
                CREATE INDEX IF NOT EXISTS idx_tasks_creator ON tasks (creator);
                CREATE INDEX IF NOT EXISTS idx_tasks_filter_combo ON tasks (status, tier, priority, id);

                CREATE INDEX IF NOT EXISTS idx_list_prop_value ON task_list_items (prop_key, prop_value, task_id);
                CREATE INDEX IF NOT EXISTS idx_list_task_prop ON task_list_items (task_id, prop_key);

                CREATE INDEX IF NOT EXISTS idx_dependencies_dep_id ON task_dependencies (dependency_id);
                CREATE INDEX IF NOT EXISTS idx_dependencies_task_id ON task_dependencies (task_id);

                CREATE INDEX IF NOT EXISTS idx_notes_task_id ON task_notes (task_id, id);

                CREATE INDEX IF NOT EXISTS idx_custom_key_value ON task_custom_values (key_name, value_text, task_id);
                CREATE INDEX IF NOT EXISTS idx_custom_task_id ON task_custom_values (task_id, key_name);
                """
            )

    def _table_exists(self, conn: sqlite3.Connection, table_name: str) -> bool:
        """Check whether a table exists.

        Args:
            conn: Open SQLite connection.
            table_name: Table name to check.

        Returns:
            True if the table exists, otherwise False.
        """
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()
        return row is not None

    def _ensure_builtin_field_definitions(self):
        """Write or repair built-in field definitions."""
        with self._connect() as conn:
            tier_def = self._get_field_definition(conn, "tier")
            default_tier = Tier.LV.value
            if tier_def and tier_def["default_value"] is not None:
                normalized_default = self._normalize_by_field_definition(tier_def, tier_def["default_value"])
                if normalized_default is not None:
                    default_tier = normalized_default

            self._upsert_field_definition_row(conn, "description", "scalar", "", [], is_builtin=True)
            self._upsert_field_definition_row(
                conn,
                "status",
                "enum",
                Status.IN_PROGRESS.value,
                [member.value for member in Status],
                is_builtin=True,
            )
            self._upsert_field_definition_row(
                conn,
                "tier",
                "enum",
                default_tier,
                [member.value for member in Tier],
                is_builtin=True,
            )
            self._upsert_field_definition_row(
                conn,
                "priority",
                "enum",
                Priority.MEDIUM.value,
                [member.value for member in Priority],
                is_builtin=True,
            )
            self._upsert_field_definition_row(conn, "collaborators", "list", None, [], is_builtin=True)
            self._upsert_field_definition_row(conn, "labels", "list", None, [], is_builtin=True)
            self._upsert_field_definition_row(conn, "dependencies", "list", None, [], is_builtin=True)

    def _upsert_field_definition_row(
            self,
            conn: sqlite3.Connection,
            key_name: str,
            value_kind: str,
            default_value: Optional[str],
            enum_values: List[str],
            *,
            is_builtin: bool,
            is_required: bool = False,
    ):
        """Insert or replace a field definition row inside a transaction.

        Args:
            conn: Open SQLite connection.
            key_name: Field key.
            value_kind: Field kind, such as scalar, enum, or list.
            default_value: Stored default value.
            enum_values: Enum options in display/storage order.
            is_builtin: Whether the field is built in.
            is_required: Whether the field is required.
        """
        if value_kind == "list":
            default_value = None
        conn.execute(
            """
            INSERT INTO field_definitions(key_name, value_kind, is_builtin, is_required, default_value, enum_values)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(key_name) DO UPDATE SET value_kind    = excluded.value_kind,
                                                is_builtin    = excluded.is_builtin,
                                                is_required   = excluded.is_required,
                                                default_value = excluded.default_value,
                                                enum_values   = excluded.enum_values
            """,
            (
                key_name,
                value_kind,
                1 if is_builtin else 0,
                1 if is_required else 0,
                default_value,
                json.dumps(enum_values, ensure_ascii=True),
            ),
        )

    def upsert_field_definition(
            self,
            key_name: str,
            value_kind: str,
            default_value: Optional[str] = None,
            enum_values: Optional[List[str]] = None,
            is_required: bool = False,
    ) -> bool:
        """Create or update a custom field definition.

        Args:
            key_name: Field key.
            value_kind: Field kind, such as scalar, enum, or list.
            default_value: Default value to store.
            enum_values: Enum options in order.
            is_required: Whether the field is required.

        Returns:
            True if the definition was stored successfully, otherwise False.
        """
        key = key_name.strip()
        if not key:
            return False
        kind = value_kind.strip().lower()
        if kind not in {"scalar", "enum", "list"}:
            return False

        options = enum_values or []
        if kind == "enum" and not options:
            return False
        if kind == "list":
            default_value = None
        elif kind == "enum":
            if default_value is None:
                default_value = str(options[0])
            else:
                normalized_default = self._normalize_enum_option(default_value, options)
                if normalized_default is None:
                    return False
                default_value = normalized_default
        elif default_value is not None:
            default_value = str(default_value)

        with self.transaction() as conn:
            self._upsert_field_definition_row(
                conn,
                key,
                kind,
                default_value,
                options,
                is_builtin=False,
                is_required=is_required,
            )
        return True

    def _is_empty_db(self) -> bool:
        """Check whether the task table is empty."""
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS cnt FROM tasks").fetchone()
            return int(row["cnt"]) == 0

    def _auto_migrate_legacy_json_if_needed(self):
        """Auto-migrate legacy JSON data into SQLite when the target DB is empty."""
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
        """Import tasks, dependencies, labels, and notes from a legacy JSON file.

        Args:
            json_path: Path to the legacy JSON file.
        """
        with open(json_path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        tasks = payload.get("tasks", {})
        tier_options = [member.value for member in Tier]
        default_tier_raw = payload.get("default_tier", Tier.LV.value)
        default_tier = self._normalize_enum_option(default_tier_raw, tier_options) or tier_options[0]

        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            self._upsert_field_definition_row(
                conn,
                "tier",
                "enum",
                default_tier,
                tier_options,
                is_builtin=True,
            )

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
                        task.get("priority", Priority.MEDIUM.value),
                        task.get("created_at", time.strftime("%Y-%m-%d %H:%M:%S")),
                        task.get("last_updated", time.strftime("%Y-%m-%d %H:%M:%S")),
                        task.get("last_editor", task.get("creator", "System")),
                    ),
                )

                for collaborator in sorted(set(task.get("collaborators", []))):
                    conn.execute(
                        "INSERT OR IGNORE INTO task_list_items(task_id, prop_key, prop_value) VALUES (?, 'collaborators', ?)",
                        (task_id, collaborator),
                    )
                for label in sorted(set(task.get("labels", []))):
                    conn.execute(
                        "INSERT OR IGNORE INTO task_list_items(task_id, prop_key, prop_value) VALUES (?, 'labels', ?)",
                        (task_id, label),
                    )
                for dep in task.get("dependencies", []):
                    if not str(dep).isdigit():
                        continue
                    dep_id = int(dep)
                    if dep_id == task_id:
                        warnings.warn(
                            f"Self-dependency detected for task {task_id} during migration; "
                            "dependency entry has been skipped."
                        )
                        continue
                    pending_dependencies.append((task_id, dep_id))
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
                cycle_path = self._dependency_cycle_path_string(conn, task_id, dep_id)
                if cycle_path:
                    warnings.warn(
                        f"Skipping circular dependency during migration: "
                        f"task {task_id} depends on {dep_id}. Cycle path: {cycle_path}"
                    )
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
        """Open an IMMEDIATE transaction and commit on success.

        Yields:
            An active SQLite connection.
        """
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

    @staticmethod
    def _parse_task_id(task_id: str) -> Optional[int]:
        """Normalize a task id to an integer.

        Args:
            task_id: Raw task id.

        Returns:
            Parsed integer id, or None if the value is invalid.
        """
        if not str(task_id).isdigit():
            return None
        return int(task_id)

    def _dependency_path(self, conn: sqlite3.Connection, start_id: int, target_id: int) -> Optional[List[int]]:
        """Find a path from one task to another in the dependency graph.

        Args:
            conn: Open SQLite connection.
            start_id: Starting task id.
            target_id: Target task id.

        Returns:
            A path as a list of ids, or None if no path exists.
        """
        rows = conn.execute("SELECT task_id, dependency_id FROM task_dependencies").fetchall()
        graph: Dict[int, List[int]] = {}
        for row in rows:
            graph.setdefault(int(row["task_id"]), []).append(int(row["dependency_id"]))

        visited: set[int] = set()

        def dfs(node: int, path: List[int]) -> Optional[List[int]]:
            if node == target_id:
                return path + [node]
            if node in visited:
                return None
            visited.add(node)
            for next_id in graph.get(node, []):
                if next_id in path:
                    continue
                found = dfs(next_id, path + [node])
                if found:
                    return found
            return None

        return dfs(start_id, [])

    def _dependency_cycle_path_string(self, conn: sqlite3.Connection, task_id: int, dependency_id: int) -> Optional[
        str]:
        """Build a human-readable circular dependency path string.

        Args:
            conn: Open SQLite connection.
            task_id: Task being updated.
            dependency_id: Dependency being added.

        Returns:
            A formatted cycle path string, or None if no cycle exists.
        """
        path = self._dependency_path(conn, dependency_id, task_id)
        if not path:
            return None
        cycle = [task_id] + path
        cycle_str = "->".join(str(i) for i in cycle)
        return f"{cycle_str}({task_id}->{task_id})"

    def _append_dependency_with_conn(
            self,
            conn: sqlite3.Connection,
            task_id: int,
            dependency_id: int,
    ) -> tuple[bool, Optional[str]]:
        """Append a dependency using an existing connection.

        Args:
            conn: Open SQLite connection.
            task_id: Task that depends on another task.
            dependency_id: Required dependency task id.

        Returns:
            A tuple of (success, cycle_path_if_any).
        """
        if task_id == dependency_id:
            return False, f"{task_id}->{dependency_id}({task_id}->{task_id})"

        task_row = conn.execute("SELECT 1 FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not task_row:
            return False, None

        dep_row = conn.execute("SELECT 1 FROM tasks WHERE id = ?", (dependency_id,)).fetchone()
        if not dep_row:
            return False, None

        cycle_path = self._dependency_cycle_path_string(conn, task_id, dependency_id)
        if cycle_path:
            return False, cycle_path

        cursor = conn.execute(
            "INSERT OR IGNORE INTO task_dependencies(task_id, dependency_id) VALUES (?, ?)",
            (task_id, dependency_id),
        )
        if cursor.rowcount == 0:
            return False, None
        return True, None

    def append_dependency(self, task_id: str, dependency_id: str, editor: str) -> tuple[bool, Optional[str]]:
        """Append a dependency and update the task editor metadata.

        Args:
            task_id: Task id to update.
            dependency_id: Dependency task id.
            editor: Name of the editor.

        Returns:
            A tuple of (success, cycle_path_if_any).
        """
        tid = self._parse_task_id(task_id)
        dep_id = self._parse_task_id(dependency_id)
        if tid is None or dep_id is None:
            return False, None

        now = time.strftime("%Y-%m-%d %H:%M:%S")
        with self.transaction() as conn:
            success, cycle_path = self._append_dependency_with_conn(conn, tid, dep_id)
            if not success:
                return False, cycle_path

            conn.execute(
                "UPDATE tasks SET last_updated = ?, last_editor = ? WHERE id = ?",
                (now, editor, tid),
            )
            return True, None

    def _fetch_builtin_list_map(
            self,
            conn: sqlite3.Connection,
            prop_key: str,
            task_ids: Optional[List[int]] = None,
    ) -> Dict[str, List[str]]:
        """Fetch built-in list values for one or more tasks.

        Args:
            conn: Open SQLite connection.
            prop_key: Built-in list field key.
            task_ids: Optional task id filter.

        Returns:
            Mapping of task id to list values.
        """
        if task_ids is None:
            rows = conn.execute(
                "SELECT task_id, prop_value FROM task_list_items WHERE prop_key = ?",
                (prop_key,),
            ).fetchall()
        elif not task_ids:
            rows = []
        else:
            placeholders = ",".join(["?"] * len(task_ids))
            rows = conn.execute(
                f"SELECT task_id, prop_value FROM task_list_items WHERE prop_key = ? AND task_id IN ({placeholders})",
                [prop_key, *task_ids],
            ).fetchall()

        result: Dict[str, List[str]] = {}
        for row in rows:
            tid = str(row["task_id"])
            result.setdefault(tid, []).append(str(row["prop_value"]))
        return result

    def _fetch_custom_scalar_map(
            self,
            conn: sqlite3.Connection,
            task_ids: Optional[List[int]] = None,
    ) -> Dict[str, Dict[str, str]]:
        """Fetch custom scalar values for one or more tasks.

        Args:
            conn: Open SQLite connection.
            task_ids: Optional task id filter.

        Returns:
            Mapping of task id to custom scalar fields.
        """
        if task_ids is None:
            rows = conn.execute("SELECT task_id, key_name, value_text FROM task_custom_values").fetchall()
        elif not task_ids:
            rows = []
        else:
            placeholders = ",".join(["?"] * len(task_ids))
            rows = conn.execute(
                f"SELECT task_id, key_name, value_text FROM task_custom_values WHERE task_id IN ({placeholders})",
                task_ids,
            ).fetchall()

        result: Dict[str, Dict[str, str]] = {}
        for row in rows:
            tid = str(row["task_id"])
            bucket = result.setdefault(tid, {})
            bucket[str(row["key_name"])] = str(row["value_text"])
        return result

    def _fetch_custom_list_map(
            self,
            conn: sqlite3.Connection,
            task_ids: Optional[List[int]] = None,
    ) -> Dict[str, Dict[str, List[str]]]:
        """Fetch custom list values for one or more tasks.

        Args:
            conn: Open SQLite connection.
            task_ids: Optional task id filter.

        Returns:
            Mapping of task id to custom list fields.
        """
        if task_ids is None:
            rows = conn.execute(
                """
                SELECT task_id, prop_key, prop_value
                FROM task_list_items
                WHERE prop_key NOT IN ('collaborators', 'labels')
                """
            ).fetchall()
        elif not task_ids:
            rows = []
        else:
            placeholders = ",".join(["?"] * len(task_ids))
            rows = conn.execute(
                f"""
                SELECT task_id, prop_key, prop_value
                FROM task_list_items
                WHERE prop_key NOT IN ('collaborators', 'labels')
                  AND task_id IN ({placeholders})
                """,
                task_ids,
            ).fetchall()

        result: Dict[str, Dict[str, List[str]]] = {}
        for row in rows:
            tid = str(row["task_id"])
            key = str(row["prop_key"])
            task_bucket = result.setdefault(tid, {})
            task_bucket.setdefault(key, []).append(str(row["prop_value"]))

        for task_bucket in result.values():
            for values in task_bucket.values():
                values.sort()
        return result

    def _fetch_notes_map(self, conn: sqlite3.Connection, task_ids: Optional[List[int]] = None) -> Dict[
        str, List[Dict[str, str]]]:
        """Fetch notes for one or more tasks.

        Args:
            conn: Open SQLite connection.
            task_ids: Optional task id filter.

        Returns:
            Mapping of task id to note records.
        """
        if task_ids is None:
            rows = conn.execute(
                "SELECT task_id, time, author, content FROM task_notes ORDER BY id "
            ).fetchall()
        elif not task_ids:
            rows = []
        else:
            placeholders = ",".join(["?"] * len(task_ids))
            rows = conn.execute(
                f"SELECT task_id, time, author, content FROM task_notes WHERE task_id IN ({placeholders}) ORDER BY id ",
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
        """Assemble database rows into the public task dictionary shape.

        Args:
            conn: Open SQLite connection.
            task_rows: Task rows fetched from the database.

        Returns:
            Mapping of task id to task objects.
        """
        task_ids = [int(row["id"]) for row in task_rows]
        collaborators = self._fetch_builtin_list_map(conn, "collaborators", task_ids)
        labels = self._fetch_builtin_list_map(conn, "labels", task_ids)

        dep_rows = []
        if task_ids:
            placeholders = ",".join(["?"] * len(task_ids))
            dep_rows = conn.execute(
                f"SELECT task_id, dependency_id FROM task_dependencies WHERE task_id IN ({placeholders})",
                task_ids,
            ).fetchall()
        deps: Dict[str, List[str]] = {}
        for row in dep_rows:
            deps.setdefault(str(row["task_id"]), []).append(str(row["dependency_id"]))

        notes = self._fetch_notes_map(conn, task_ids)
        custom_scalars = self._fetch_custom_scalar_map(conn, task_ids)
        custom_lists = self._fetch_custom_list_map(conn, task_ids)
        custom_def_rows = conn.execute(
            "SELECT key_name, value_kind FROM field_definitions WHERE is_builtin = 0"
        ).fetchall()
        custom_scalar_keys = [str(row["key_name"]) for row in custom_def_rows if str(row["value_kind"]).lower() != "list"]
        custom_list_keys = [str(row["key_name"]) for row in custom_def_rows if str(row["value_kind"]).lower() == "list"]

        result: Dict[str, Dict[str, Any]] = {}
        for row in task_rows:
            tid = str(row["id"])
            dep_list = deps.get(tid, [])
            dep_list.sort(key=lambda x: int(x) if str(x).isdigit() else str(x))
            collab_list = sorted(collaborators.get(tid, []))
            label_list = sorted(labels.get(tid, []))

            task_obj: Dict[str, Any] = {
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

            scalar_custom = dict(custom_scalars.get(tid, {}))
            for key in custom_scalar_keys:
                scalar_custom.setdefault(key, "")

            list_custom = dict(custom_lists.get(tid, {}))
            for key in custom_list_keys:
                list_custom.setdefault(key, [])

            task_obj["custom"] = scalar_custom
            task_obj["custom_lists"] = list_custom

            for key, val in scalar_custom.items():
                if key not in task_obj:
                    task_obj[key] = val

            result[tid] = task_obj
        return result

    def _get_tasks_by_ids(self, conn: sqlite3.Connection, task_ids: List[int]) -> Dict[str, Dict[str, Any]]:
        """Fetch tasks by a list of ids.

        Args:
            conn: Open SQLite connection.
            task_ids: Task ids to fetch.

        Returns:
            Mapping of task id to task objects.
        """
        if not task_ids:
            return {}
        placeholders = ",".join(["?"] * len(task_ids))
        rows = conn.execute(
            f"SELECT * FROM tasks WHERE id IN ({placeholders}) ORDER BY id ",
            task_ids,
        ).fetchall()
        return self._assemble_tasks_from_rows(conn, rows)

    def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """Fetch all tasks."""
        with self._connect() as conn:
            task_rows = conn.execute("SELECT * FROM tasks ORDER BY id ").fetchall()
            return self._assemble_tasks_from_rows(conn, task_rows)

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single task by id.

        Args:
            task_id: Task id to fetch.

        Returns:
            The task object, or None when the task does not exist.
        """
        if not str(task_id).isdigit():
            return None
        with self._connect() as conn:
            tasks = self._get_tasks_by_ids(conn, [int(task_id)])
            return tasks.get(str(task_id))

    @staticmethod
    def _escape_like_fragment(raw: str) -> str:
        """Escape SQL LIKE wildcard characters."""
        return raw.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    def search_tasks(self, criteria: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
        """Search tasks by title, status, tier, dependencies, and custom fields.

        Args:
            criteria: Search conditions keyed by field name.

        Returns:
            Mapping of task id to matching task objects.
        """
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

        list_aliases = {
            "collaborator": "collaborators",
            "label": "labels",
        }
        for key, prop_key in list_aliases.items():
            val = criteria.get(key)
            if val is None:
                continue
            neg = val.startswith("!")
            target = val[1:] if neg else val
            # noinspection SqlResolve
            base = (
                "SELECT 1 FROM task_list_items x "
                "WHERE x.task_id = t.id AND x.prop_key = ? AND LOWER(x.prop_value) = LOWER(?)"
            )
            where_clauses.append(f"NOT EXISTS ({base})" if neg else f"EXISTS ({base})")
            params.extend([prop_key, target])

        dep_val = criteria.get("dependency") or criteria.get("dependencies")
        if dep_val is not None:
            neg = dep_val.startswith("!")
            target = dep_val[1:] if neg else dep_val
            if not str(target).isdigit():
                return {}
            # noinspection SqlResolve
            base = (
                "SELECT 1 FROM task_dependencies d "
                "WHERE d.task_id = t.id AND d.dependency_id = ?"
            )
            where_clauses.append(f"NOT EXISTS ({base})" if neg else f"EXISTS ({base})")
            params.append(int(target))

        reserved = {"title", "status", "tier", "priority", "creator", "collaborator", "label", "dependency",
                    "dependencies"}
        for key, val in criteria.items():
            if key in reserved:
                continue

            neg = str(val).startswith("!")
            target = str(val)[1:] if neg else str(val)
            # noinspection SqlResolve
            scalar_exists = (
                "SELECT 1 FROM task_custom_values cv "
                "WHERE cv.task_id = t.id AND LOWER(cv.key_name) = LOWER(?) AND LOWER(cv.value_text) = LOWER(?)"
            )
            # noinspection SqlResolve
            list_exists = (
                "SELECT 1 FROM task_list_items li "
                "WHERE li.task_id = t.id AND LOWER(li.prop_key) = LOWER(?) AND LOWER(li.prop_value) = LOWER(?)"
            )
            if neg:
                where_clauses.append(f"NOT EXISTS ({scalar_exists}) AND NOT EXISTS ({list_exists})")
            else:
                where_clauses.append(f"(EXISTS ({scalar_exists}) OR EXISTS ({list_exists}))")
            params.extend([key, target, key, target])

        sql = "SELECT t.id FROM tasks t"
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        sql += " ORDER BY t.id ASC"

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            task_ids = [int(row["id"]) for row in rows]
            return self._get_tasks_by_ids(conn, task_ids)

    def task_exists(self, task_id: str) -> bool:
        """Check whether a task exists.

        Args:
            task_id: Task id to check.

        Returns:
            True if the task exists, otherwise False.
        """
        if not str(task_id).isdigit():
            return False
        with self._connect() as conn:
            row = conn.execute("SELECT 1 FROM tasks WHERE id = ?", (int(task_id),)).fetchone()
            return row is not None

    @property
    def data(self) -> Dict[str, Any]:
        """Compatibility snapshot for legacy callers.

        Returns:
            A dictionary containing tasks, next_id, and default_tier.
        """
        warnings.warn(
            "TodoManager.data is deprecated; use repository query methods directly.",
            DeprecationWarning,
            stacklevel=2,
        )
        tasks = self.get_all_tasks()
        with self._connect() as conn:
            tier_def = self._get_field_definition(conn, "tier")
            default_tier = Tier.LV.value
            if tier_def and tier_def["default_value"] is not None:
                normalized_default = self._normalize_by_field_definition(tier_def, tier_def["default_value"])
                if normalized_default is not None:
                    default_tier = normalized_default
            row = conn.execute("SELECT COALESCE(MAX(id), 0) AS max_id FROM tasks").fetchone()
            next_id = int(row["max_id"]) + 1
        return {"tasks": tasks, "next_id": next_id, "default_tier": default_tier}

    def set_default_tier(self, tier: str):
        """Compatibility wrapper that delegates to the tier default setting.

        Args:
            tier: New default tier value.
        """
        warnings.warn(
            "TodoManager.set_default_tier is deprecated; set defaults via field definitions.",
            DeprecationWarning,
            stacklevel=2,
        )
        validated = Tier.validate(tier)
        if not validated:
            return False
        return self.set_field_default("tier", validated)

    def _get_field_definition(self, conn: sqlite3.Connection, key_name: str) -> Optional[sqlite3.Row]:
        """Read a raw field definition row from the database.

        Args:
            conn: Open SQLite connection.
            key_name: Field key.

        Returns:
            The raw SQLite row, or None if the field does not exist.
        """
        return conn.execute(
            "SELECT key_name, value_kind, is_required, default_value, enum_values FROM field_definitions WHERE key_name = ?",
            (key_name,),
        ).fetchone()

    def get_field_definition(self, key_name: str) -> Optional[Dict[str, Any]]:
        """Fetch a field definition and deserialize enum options.

        Args:
            key_name: Field key.

        Returns:
            A dictionary describing the field, or None if not found.
        """
        normalized_key = str(key_name).strip()
        if not normalized_key:
            return None

        with self._connect() as conn:
            row = self._get_field_definition(conn, normalized_key)
            if row is None:
                return None

            try:
                enum_values = json.loads(row["enum_values"] or "[]")
            except json.JSONDecodeError:
                enum_values = []

            return {
                "key_name": str(row["key_name"]),
                "value_kind": str(row["value_kind"]),
                "is_required": bool(row["is_required"]),
                "default_value": row["default_value"],
                "enum_values": [str(option) for option in enum_values],
            }

    def set_field_default(self, key_name: str, default_value: str) -> bool:
        """Update the default value stored in a field definition.

        Args:
            key_name: Field key.
            default_value: New default value.

        Returns:
            True if the update succeeded, otherwise False.
        """
        normalized_key = str(key_name).strip()
        if not normalized_key:
            return False

        with self.transaction() as conn:
            row = self._get_field_definition(conn, normalized_key)
            if row is None:
                return False

            value_kind = str(row["value_kind"]).lower()
            if value_kind == "list":
                return False

            normalized_default = str(default_value)
            if value_kind == "enum":
                normalized_default = self._normalize_by_field_definition(row, default_value)
                if normalized_default is None:
                    return False

            conn.execute(
                "UPDATE field_definitions SET default_value = ? WHERE key_name = ?",
                (normalized_default, normalized_key),
            )
            return True

    @staticmethod
    def _normalize_enum_option(value: Any, options: List[str]) -> Optional[str]:
        """Normalize an enum input by ordered id or option key.

        Args:
            value: Raw input value.
            options: Ordered enum option keys.

        Returns:
            The normalized option key, or None if invalid.
        """
        raw = str(value).strip()
        if raw.isdigit():
            idx = int(raw)
            if 0 <= idx < len(options):
                return str(options[idx])

        lowered = raw.lower()
        for option in options:
            text = str(option)
            if text.lower() == lowered:
                return text
        return None

    def _normalize_by_field_definition(self, definition: sqlite3.Row, value: Any) -> Optional[str]:
        """Normalize a value using the stored field definition.

        Args:
            definition: Raw field definition row.
            value: Raw input value.

        Returns:
            The normalized value, or None if invalid.
        """
        value_kind = str(definition["value_kind"]).lower()
        val = str(value)
        if value_kind != "enum":
            return val

        try:
            options = json.loads(definition["enum_values"] or "[]")
        except json.JSONDecodeError:
            options = []
        if not options:
            return None
        return self._normalize_enum_option(val, [str(option) for option in options])

    def _core_defaults(self, conn: sqlite3.Connection) -> Dict[str, str]:
        """Resolve default values for core fields."""
        defaults = {
            "description": "",
            "status": Status.IN_PROGRESS.value,
            "tier": Tier.LV.value,
            "priority": Priority.MEDIUM.value,
        }
        rows = conn.execute(
            "SELECT key_name, value_kind, default_value, enum_values FROM field_definitions WHERE key_name IN ('description', 'status', 'tier', 'priority')"
        ).fetchall()
        for row in rows:
            key = str(row["key_name"])
            kind = str(row["value_kind"]).lower()

            if kind == "enum":
                try:
                    options = [str(option) for option in json.loads(row["enum_values"] or "[]")]
                except json.JSONDecodeError:
                    options = []

                if not options:
                    warnings.warn(f"Enum field '{key}' has no options and will be ignored.")
                    continue

                normalized = self._normalize_by_field_definition(row, row["default_value"]) if row["default_value"] is not None else None
                defaults[key] = normalized if normalized is not None else options[0]
                continue

            if row["default_value"] is not None:
                defaults[key] = str(row["default_value"])
        return defaults

    def _custom_field_initial_values(self, conn: sqlite3.Connection) -> List[Tuple[str, str]]:
        """Resolve custom field defaults used when creating a task."""
        rows = conn.execute(
            """
            SELECT key_name, value_kind, default_value, enum_values
            FROM field_definitions
            WHERE is_builtin = 0
              AND value_kind IN ('scalar', 'enum')
            """
        ).fetchall()

        defaults: List[Tuple[str, str]] = []
        for row in rows:
            value_kind = str(row["value_kind"]).lower()
            raw_default = row["default_value"]
            if value_kind == "enum":
                try:
                    options = [str(option) for option in json.loads(row["enum_values"] or "[]")]
                except json.JSONDecodeError:
                    options = []

                if not options:
                    warnings.warn(f"Enum field '{row['key_name']}' has no options and will be ignored.")
                    continue

                normalized = self._normalize_by_field_definition(row, raw_default) if raw_default is not None else None
                if normalized is None:
                    normalized = options[0]
            elif raw_default is None:
                normalized = ""
            else:
                normalized = str(raw_default)
            defaults.append((str(row["key_name"]), normalized))
        return defaults

    def add_task(self, title: str, creator: str) -> str:
        """Create a task and initialize core/custom default values.

        Args:
            title: Task title.
            creator: Task creator.

        Returns:
            The new task id as a string.
        """
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        with self.transaction() as conn:
            defaults = self._core_defaults(conn)
            cursor = conn.execute(
                """
                INSERT INTO tasks(title, creator, description, status, tier, priority,
                                  created_at, last_updated, last_editor)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    title,
                    creator,
                    defaults.get("description", ""),
                    defaults.get("status", Status.IN_PROGRESS.value),
                    defaults.get("tier", Tier.LV.value),
                    defaults.get("priority", Priority.MEDIUM.value),
                    now,
                    now,
                    creator,
                ),
            )
            task_id = int(cursor.lastrowid)

            for key_name, default_val in self._custom_field_initial_values(conn):
                conn.execute(
                    "INSERT OR IGNORE INTO task_custom_values(task_id, key_name, value_text) VALUES (?, ?, ?)",
                    (task_id, key_name, default_val),
                )

            return str(task_id)

    @staticmethod
    def _sort_collection(collection: List, key_type: str):
        """Sort collection values with dependency-aware ordering.

        Args:
            collection: Values to sort in place.
            key_type: Logical field key.
        """
        if key_type == "dependencies":
            collection.sort(key=lambda x: int(x) if str(x).isdigit() else str(x))
        else:
            collection.sort()

    def update_task(self, task_id: str, key: str, value: Any, editor: str) -> bool:
        """Update a task's core, list, or custom field.

        Args:
            task_id: Task id to update.
            key: Field key.
            value: New value.
            editor: Name of the editor.

        Returns:
            True if the update succeeded, otherwise False.
        """
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        with self.transaction() as conn:
            tid = self._parse_task_id(task_id)
            if tid is None:
                return False
            task_row = conn.execute("SELECT 1 FROM tasks WHERE id = ?", (tid,)).fetchone()
            if not task_row:
                return False

            normalized_key = str(key).strip()
            if not normalized_key:
                return False

            if normalized_key in BUILTIN_LIST_FIELDS:
                cursor = conn.execute(
                    "INSERT OR IGNORE INTO task_list_items(task_id, prop_key, prop_value) VALUES (?, ?, ?)",
                    (tid, normalized_key, str(value)),
                )
                if cursor.rowcount == 0:
                    return False

            elif normalized_key == "dependencies":
                if not str(value).isdigit():
                    return False
                success, _cycle_path = self._append_dependency_with_conn(conn, tid, int(value))
                if not success:
                    return False

            elif normalized_key in CORE_SCALAR_FIELDS:
                if normalized_key in {"status", "tier", "priority"}:
                    definition = self._get_field_definition(conn, normalized_key)
                    if definition is not None:
                        normalized_value = self._normalize_by_field_definition(definition, value)
                        if normalized_value is None:
                            return False
                    else:
                        normalized_value = str(value)
                else:
                    normalized_value = str(value)

                conn.execute(f"UPDATE tasks SET {normalized_key} = ? WHERE id = ?", (normalized_value, tid))

            else:
                definition = self._get_field_definition(conn, normalized_key)

                if definition is None:
                    return False

                if str(definition["value_kind"]).lower() == "list":
                    cursor = conn.execute(
                        "INSERT OR IGNORE INTO task_list_items(task_id, prop_key, prop_value) VALUES (?, ?, ?)",
                        (tid, normalized_key, str(value)),
                    )
                    if cursor.rowcount == 0:
                        return False
                else:
                    normalized_value = self._normalize_by_field_definition(definition, value)
                    if normalized_value is None:
                        return False
                    conn.execute(
                        """
                        INSERT INTO task_custom_values(task_id, key_name, value_text)
                        VALUES (?, ?, ?)
                        ON CONFLICT(task_id, key_name) DO UPDATE SET value_text = excluded.value_text
                        """,
                        (tid, normalized_key, normalized_value),
                    )

            conn.execute(
                "UPDATE tasks SET last_updated = ?, last_editor = ? WHERE id = ?",
                (now, editor, tid),
            )
            return True

    def remove_item(self, task_id: str, key: str, value: str, editor: str) -> bool:
        """Remove a value from a list field or dependency field.

        Args:
            task_id: Task id to update.
            key: Field key.
            value: Value to remove.
            editor: Name of the editor.

        Returns:
            True if the removal succeeded, otherwise False.
        """
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        with self.transaction() as conn:
            tid = self._parse_task_id(task_id)
            if tid is None:
                return False
            task_row = conn.execute("SELECT 1 FROM tasks WHERE id = ?", (tid,)).fetchone()
            if not task_row:
                return False

            normalized_key = str(key).strip()
            if normalized_key == "dependencies":
                if not str(value).isdigit():
                    return False
                cursor = conn.execute(
                    "DELETE FROM task_dependencies WHERE task_id = ? AND dependency_id = ?",
                    (tid, int(value)),
                )
            else:
                cursor = conn.execute(
                    "DELETE FROM task_list_items WHERE task_id = ? AND prop_key = ? AND prop_value = ?",
                    (tid, normalized_key, str(value)),
                )

            if cursor.rowcount == 0:
                return False

            conn.execute(
                "UPDATE tasks SET last_updated = ?, last_editor = ? WHERE id = ?",
                (now, editor, tid),
            )
            return True

    def add_note(self, task_id: str, content: str, author: str) -> bool:
        """Append a note to a task and update its edit timestamp.

        Args:
            task_id: Task id to update.
            content: Note content.
            author: Note author.

        Returns:
            True if the note was added, otherwise False.
        """
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        with self.transaction() as conn:
            tid = self._parse_task_id(task_id)
            if tid is None:
                return False
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
