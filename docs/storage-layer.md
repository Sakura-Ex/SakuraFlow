# Sakura Flow 存储层数据结构

> 基于当前实现整理（`sakura_flow/manager.py`、`sakura_flow/__init__.py`、`__main__.py`、`sakura_flow/config_loader.py`）。

## 1. 数据位置与初始化

- 主存储为 SQLite：`sf_tasks/tasks.db`
- 旧版迁移源：`sf_tasks/tasks.json`
- 自定义字段配置：`config/sakura_flow/custom_fields.yml`
- 启动入口：
  - MCDR：`sakura_flow/__init__.py:on_load`
  - CLI：`__main__.py:main`

`TodoManager` 初始化顺序（`sakura_flow/manager.py`）：
1. `_init_db()`：建表 + 索引
2. `_ensure_builtin_field_definitions()`：写入/修正内建字段定义
4. `_auto_migrate_legacy_json_if_needed()`：在 DB 为空时迁移 `tasks.json`

## 2. SQLite 表结构

### `meta`

| 列名      | 类型            | 说明   |
|---------|---------------|------|
| `key`   | TEXT PK       | 元数据键 |
| `value` | TEXT NOT NULL | 元数据值 |

当前关键键：
- 当前实现未使用固定关键键（保留作扩展元数据容器）

---

### `tasks`

| 列名             | 类型                       | 说明     |
|----------------|--------------------------|--------|
| `id`           | INTEGER PK AUTOINCREMENT | 任务 ID  |
| `title`        | TEXT NOT NULL            | 标题     |
| `creator`      | TEXT NOT NULL            | 创建者    |
| `description`  | TEXT NOT NULL DEFAULT '' | 描述     |
| `status`       | TEXT NOT NULL            | 状态     |
| `tier`         | TEXT NOT NULL            | 等级     |
| `priority`     | TEXT NOT NULL            | 优先级    |
| `created_at`   | TEXT NOT NULL            | 创建时间   |
| `last_updated` | TEXT NOT NULL            | 最近更新时间 |
| `last_editor`  | TEXT NOT NULL            | 最近编辑者  |

---

### `field_definitions`

用于定义“可写字段模型”（内建字段 + 自定义字段）。

| 列名              | 类型                         | 说明                       |
|-----------------|----------------------------|--------------------------|
| `key_name`      | TEXT PK                    | 字段键名                     |
| `value_kind`    | TEXT NOT NULL              | `scalar`/`enum`/`list`   |
| `is_builtin`    | INTEGER NOT NULL DEFAULT 0 | 是否内建字段                   |
| `is_required`   | INTEGER NOT NULL DEFAULT 0 | 是否必填                     |
| `default_value` | TEXT NULL                  | 默认值（`list` 类型强制为 `NULL`） |
| `enum_values`   | TEXT NOT NULL DEFAULT '[]' | 枚举选项（JSON 字符串，顺序即 0-based id） |

内建字段（初始化写入）：
- `description`(scalar)
- `status`(enum)
- `tier`(enum)
- `priority`(enum)
- `collaborators`(list)
- `labels`(list)
- `dependencies`(list)

---

### `task_custom_values`

自定义标量/枚举值落盘表。

| 列名           | 类型                                      | 说明    |
|--------------|-----------------------------------------|-------|
| `task_id`    | INTEGER FK -> `tasks.id`                | 任务 ID |
| `key_name`   | TEXT FK -> `field_definitions.key_name` | 字段键名  |
| `value_text` | TEXT NOT NULL                           | 字段值   |

主键：`(task_id, key_name)`

---

### `task_list_items`

所有“列表字段”统一落盘（包括内建列表和自定义列表）。

| 列名           | 类型                       | 说明     |
|--------------|--------------------------|--------|
| `task_id`    | INTEGER FK -> `tasks.id` | 任务 ID  |
| `prop_key`   | TEXT NOT NULL            | 列表字段键名 |
| `prop_value` | TEXT NOT NULL            | 列表项值   |

主键：`(task_id, prop_key, prop_value)`

说明：
- 内建 `collaborators`/`labels` 也在该表存储。
- `dependencies` 不在此表，单独使用 `task_dependencies`。

---

### `task_dependencies`

任务依赖关系表（有向边：`task_id -> dependency_id`）。

| 列名              | 类型                       | 说明   |
|-----------------|--------------------------|------|
| `task_id`       | INTEGER FK -> `tasks.id` | 当前任务 |
| `dependency_id` | INTEGER FK -> `tasks.id` | 依赖任务 |

主键：`(task_id, dependency_id)`

约束语义（业务层 + 存储层实现）：
- 禁止自依赖
- 依赖任务必须存在
- 禁止形成环

---

### `task_notes`

任务进度记录。

| 列名        | 类型                       | 说明    |
|-----------|--------------------------|-------|
| `id`      | INTEGER PK AUTOINCREMENT | 记录 ID |
| `task_id` | INTEGER FK -> `tasks.id` | 任务 ID |
| `time`    | TEXT NOT NULL            | 时间    |
| `author`  | TEXT NOT NULL            | 作者    |
| `content` | TEXT NOT NULL            | 内容    |

## 3. 索引

当前实现创建了以下主要索引（`_init_db`）：

- `tasks`：`status`、`tier`、`priority`、`creator`、`(status, tier, priority, id)`
- `task_list_items`：`(prop_key, prop_value, task_id)`、`(task_id, prop_key)`
- `task_dependencies`：`dependency_id`、`task_id`
- `task_notes`：`(task_id, id)`
- `task_custom_values`：`(key_name, value_text, task_id)`、`(task_id, key_name)`

## 4. 运行时任务对象结构（读模型）

对外返回任务对象（见 `_assemble_tasks_from_rows`）大致为：

```python
{
  "title": str,
  "creator": str,
  "description": str,
  "status": str,
  "tier": str,
  "priority": str,
  "labels": list[str],
  "collaborators": list[str],
  "dependencies": list[str],
  "notes": [
    {"time": str, "author": str, "content": str}
  ],
  "created_at": str,
  "last_updated": str,
  "last_editor": str,
  "custom": dict[str, str],          # 自定义 scalar/enum
  "custom_lists": dict[str, list[str]]
}
```

补充：
- `custom` 中的键会在组装时“平铺”到任务顶层（若不与核心键冲突）。
- `dependencies` 会按数字语义排序。
- 自定义字段会在任务组装时“补齐键”：
  - 自定义 `scalar/enum` 缺失时补空字符串 `""`
  - 自定义 `list` 缺失时补空列表 `[]`

## 5. 写入路径与字段归属

- `add_task(...)`
  - 写入 `tasks`
  - 按 `field_definitions` 写入 `task_custom_values`（所有自定义 `scalar/enum` 字段都会初始化）
  - `enum` 默认值策略：
    - 若定义了合法默认值，使用该值
    - 若未定义/无效，回退到枚举选项第 0 项
- `update_task(task_id, key, value, editor)`
  - 核心标量键（`title/description/status/tier/priority`）更新 `tasks`
  - `dependencies` 走 `task_dependencies`
  - 内建列表键（`collaborators/labels`）写 `task_list_items`
  - 自定义字段：
    - `list` -> `task_list_items`
    - `scalar/enum` -> `task_custom_values`
- `remove_item(...)`
  - `dependencies` 从 `task_dependencies` 删除
  - 其他列表字段从 `task_list_items` 删除
- `add_note(...)`
  - 写 `task_notes`

以上写入都会更新 `tasks.last_updated` 与 `tasks.last_editor`（新增任务除外由插入时赋值）。

## 6. 兼容与迁移

### 6.1 旧 JSON 自动迁移

当满足以下条件时，`tasks.json` 会自动迁移到 SQLite：
- 配置了 `legacy_json_path`
- 文件存在
- 当前 `tasks` 表为空

迁移后会生成 `tasks.json.bak`（若不存在）。

### 6.2 老表兼容迁移

当前实现无旧 list 表自动迁移流程；已支持的兼容迁移入口为 `tasks.json -> sqlite`。

## 7. 自定义字段配置与约束

自定义字段来源：`config/sakura_flow/custom_fields.yml`（缺失时自动按模板生成）。

关键约束（`sakura_flow/config_loader.py`）：
- 字段名不能与核心字段冲突（如 `status`、`dependencies`）
- 不能占用保留搜索键（如 `creator`、`label`）
- 不能与内建别名冲突（`PROP_ALIASES`/`LIST_PROP_ALIASES`）
- `enum` 必须有非空 `enum_values`；否则该字段会被忽略并给出 warning
- `enum_values` 支持两种写法：
  - 简写字符串：`[early, mid, late]`
- 对象写法：`[{key: early, label: ...}, ...]`
- 枚举内部持久化使用 `key`（字符串），`id` 仅由列表顺序派生（0-based）
- 枚举 `id` 语义始终由配置顺序决定，配置对象里的显式 `id` 字段会被忽略
- `enum default_value` 支持 key 或数字 id；未定义/无效时回退第 0 项
- `list` 类型默认值会被清空（不支持默认列表）

## 8. 事务与一致性

`TodoManager.transaction` 使用：
- `BEGIN IMMEDIATE`
- 异常回滚
- 成功提交

这保证了单次写操作的原子性，并减少并发写下的不一致风险。
