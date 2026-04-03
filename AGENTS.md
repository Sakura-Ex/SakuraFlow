# AGENTS.md

## Purpose

- `Sakura Flow` is an MCDReforged plugin for in-game todo management with dependency tracking and clickable chat UI (
  `README.md`, `sakura_flow/interface.py`).
- Main command surface is `!!sf` (`sakura_flow/constants.py`), with rich text interaction (hover, suggest command,
  buttons).

## Architecture Map

- Plugin entrypoint: `sakura_flow/__init__.py:on_load` creates `TodoManager`, applies custom field definitions from
  `config/sakura_flow/custom_fields.yml`, creates `TodoApplication`, then registers commands through
  `register_mcdr_commands`.
- Command layer: `sakura_flow/mcdr_entry.py` parses MCDR command tree and delegates business logic to `TodoApplication`.
- Application layer: `sakura_flow/application/facade.py` orchestrates use cases and search cache (`SearchCache`, default
  TTL 300s).
- Use-case layer: `sakura_flow/application/use_cases/*.py` implements query/mutation rules and validation.
- Ports layer: `sakura_flow/ports/repository.py` defines repository contract for hexagonal boundaries.
- Persistence layer: `sakura_flow/manager.py` owns SQLite storage (`sf_tasks/tasks.db`) and transaction flow (
  `BEGIN IMMEDIATE -> mutate -> commit`).
- Presentation layer: `sakura_flow/interface.py` renders all MCDR `RText`/`RTextList` UI, including hover details and
  pagination.
- Help surface catalog: `sakura_flow/help_core/*` is the single command-help source used by both MCDR help rendering
  (`UI.render_help`) and CLI help rendering (`render_cli`).
- Shared domain config: `sakura_flow/enums.py` (`Status`, `Priority`, `Tier`) + `sakura_flow/constants.py` (aliases,
  command prefix, page size).

## Data and State Flow

- Persistent data path is expected at `sf_tasks/tasks.db` under MCDR root (`sakura_flow/__init__.py`, `__main__.py`).
- Custom field config is loaded from `config/sakura_flow/custom_fields.yml`; missing file is created from
  `sakura_flow/templates/custom_fields.template.yml` (`sakura_flow/config_loader.py`).
- Legacy JSON (`sf_tasks/tasks.json`) is auto-migrated on startup when the DB is empty, with a `.bak` backup kept.
- Task schema is effectively defined in `TodoManager.add_task` (fields: `status`, `tier`, `priority`, `dependencies`,
  `notes`, timestamps, editors), with dynamic custom scalar/list fields materialized from `field_definitions`
  (`sakura_flow/manager.py`).
- `tier` default source is `field_definitions` (`key_name='tier'`), not `meta.default_tier`.
- List fields (`dependencies`, `collaborators`, `labels`) are deduped and sorted in `TodoManager.update_task`.
- Dependencies are validated on append for existence, self-dependency, and cycle detection
  (`task_mutations.append_list_property`, `TodoManager.append_dependency`).
- Search supports negation syntax (`!Done`, `!player`) and fuzzy title contains (`TodoManager.search_tasks`).

## Developer Workflows

- Install deps:

```bash
pip install -r requirements.txt
```

- Run tests (command surfaces, config loader, interface rendering, sqlite storage, and i18n key checks):

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
- Custom field key names must not collide with protected core keys, reserved search keys, or built-in aliases
  (`sakura_flow/config_loader.py`: `PROTECTED_CORE_KEYS`, `RESERVED_KEYS`, `PROP_ALIASES`, `LIST_PROP_ALIASES`).
- For enum custom fields, persist/use stable option `key` values; treat numeric id as 0-based order mapping only.
- Keep enum option order stable: config list order defines id mapping (`0..n-1`); ignore any explicit per-option `id`
  metadata in config objects.
- Keep command additions mirrored in help catalog (`sakura_flow/help_core/catalog.py`), help UI
  (`UI.render_help`), and both command frontends when relevant (MCDR + CLI).

## Integration Points and Risks

- External runtime dependency is `mcdreforged>=2.15.0` (`requirements.txt`, `mcdreforged.plugin.json`).
- Config parsing depends on `PyYAML>=6.0` (`requirements.txt`); invalid custom field entries are ignored with warnings
  from `apply_custom_field_definitions`.
- Plugin metadata is in `mcdreforged.plugin.json`; keep id/version/dependency aligned with code behavior.
- `TodoManager` relies on SQLite locking/transactions; preserve atomic transaction boundaries when changing write paths.
- `interface.py` consumes plain task dictionaries; keep frontend adapters (`mcdr_entry.py`, `cli_entry.py`) responsible
  for fetching snapshots.

