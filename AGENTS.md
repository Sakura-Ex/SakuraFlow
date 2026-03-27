# AGENTS.md

## Purpose

- `Sakura Flow` is an MCDReforged plugin for in-game todo management with dependency tracking and clickable chat UI (
  `README.md`, `sakura_flow/interface.py`).
- Main command surface is `!!todo` (`sakura_flow/constants.py`), with rich text interaction (hover, suggest command,
  buttons).

## Architecture Map

- Plugin entrypoint: `sakura_flow/__init__.py:on_load` creates `TodoManager` and `TodoApplication`, then registers
  commands through `register_mcdr_commands`.
- Command layer: `sakura_flow/mcdr_entry.py` parses MCDR command tree and delegates business logic to `TodoApplication`.
- Application layer: `sakura_flow/application/facade.py` orchestrates use cases and search cache (`SearchCache`, default
  TTL 300s).
- Use-case layer: `sakura_flow/application/use_cases/*.py` implements query/mutation rules and validation.
- Ports layer: `sakura_flow/ports/repository.py` defines repository contract for hexagonal boundaries.
- Persistence layer: `sakura_flow/manager.py` owns SQLite storage (`sf_tasks/tasks.db`) and transaction flow (
  `BEGIN IMMEDIATE -> mutate -> commit`).
- Presentation layer: `sakura_flow/interface.py` renders all MCDR `RText`/`RTextList` UI, including hover details and
  pagination.
- Shared domain config: `sakura_flow/enums.py` (`Status`, `Priority`, `Tier`) + `sakura_flow/constants.py` (aliases,
  command prefix, page size).

## Data and State Flow

- Persistent data path is expected at `sf_tasks/tasks.db` under MCDR root (`sakura_flow/__init__.py`, `__main__.py`).
- Legacy JSON (`sf_tasks/tasks.json`) is auto-migrated on startup when the DB is empty, with a `.bak` backup kept.
- Task schema is effectively defined in `TodoManager.add_task` (fields: `status`, `tier`, `priority`, `dependencies`,
  `notes`, timestamps, editors).
- List fields (`dependencies`, `collaborators`, `labels`) are deduped and sorted in `TodoManager.update_task`.
- Dependencies are validated only on append (`task_mutations.append_list_property` requires target task id to exist).
- Search supports negation syntax (`!Done`, `!player`) and fuzzy title contains (`TodoManager.search_tasks`).

## Developer Workflows

- Install deps:

```bash
pip install -r requirements.txt
```

- Run tests (current suite is smoke + command registration + i18n key checks):

```bash
pytest
```

- Run CLI mode from repo root:

```bash
python -m sakura_flow add "Task title"
python -m sakura_flow list --all
```

- CLI command wiring is in `sakura_flow/cli_entry.py`; MCDR command wiring is separate in `sakura_flow/mcdr_entry.py`.

## Project-Specific Conventions

- Treat alias dictionaries in `constants.py` as source of truth for set/append/remove property names.
- Prefer enum validation (`Tier.validate`, `Priority.validate`, `Status.validate`) over manual string checks.
- UI strings must come from translation keys (`server.tr(...)`), not hardcoded user-facing text.
- Translation key coverage is enforced by `tests/test_translation_keys.py` (AST scan for `sakuraflow.*` literals).
- Keep command additions mirrored in help UI (`UI.render_help`) and in both command frontends when relevant (MCDR +
  CLI).

## Integration Points and Risks

- External runtime dependency is `mcdreforged>=2.15.0` (`requirements.txt`, `mcdreforged.plugin.json`).
- Plugin metadata is in `mcdreforged.plugin.json`; keep id/version/dependency aligned with code behavior.
- `TodoManager` relies on SQLite locking/transactions; preserve atomic transaction boundaries when changing write paths.
- `interface.py` consumes plain task dictionaries; keep frontend adapters (`mcdr_entry.py`, `cli_entry.py`) responsible
  for fetching snapshots.

