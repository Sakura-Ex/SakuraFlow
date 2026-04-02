import os
from importlib import resources
from typing import Any, Dict, List, Tuple

import yaml

from .constants import LIST_PROP_ALIASES, PROP_ALIASES

# Core fields are fixed plugin behavior and cannot be overridden by user config.
PROTECTED_CORE_KEYS = {
    "title",
    "description",
    "status",
    "tier",
    "priority",
    "collaborators",
    "labels",
    "dependencies",
}

# Reserved search keys from query parser/runtime.
RESERVED_KEYS = {
    "creator",
    "collaborator",
    "label",
    "dependency",
}

DEFAULT_CUSTOM_FIELDS_FALLBACK = """version: 1
custom_fields: []
"""


def _load_template_text(template_path: str | None = None) -> str:
    # Explicit template path is primarily used by tests and local overrides.
    if template_path and os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()

    # Supports zipped/pyz execution where package files are not normal paths.
    try:
        return resources.files("sakura_flow").joinpath("templates/custom_fields.template.yml").read_text(
            encoding="utf-8")
    except Exception:
        return DEFAULT_CUSTOM_FIELDS_FALLBACK


def _normalize_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    key_name = str(entry.get("key_name") or entry.get("key") or "").strip()
    value_kind = str(entry.get("value_kind") or entry.get("type") or "scalar").strip().lower()
    default_value = entry.get("default_value", entry.get("default"))
    enum_values = entry.get("enum_values", entry.get("options"))
    is_required = bool(entry.get("is_required", entry.get("required", False)))

    normalized = {
        "key_name": key_name,
        "value_kind": value_kind,
        "default_value": default_value,
        "enum_values": enum_values,
        "is_required": is_required,
    }
    return normalized


def ensure_custom_fields_config(config_path: str, template_path: str | None = None):
    config_dir = os.path.dirname(config_path)
    os.makedirs(config_dir, exist_ok=True)
    if not os.path.exists(config_path):
        template_text = _load_template_text(template_path)
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(template_text)


def load_custom_field_definitions(config_path: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    ensure_custom_fields_config(config_path)

    with open(config_path, "r", encoding="utf-8") as f:
        payload = yaml.safe_load(f) or {}

    warnings: List[str] = []
    if not isinstance(payload, dict):
        return [], ["custom_fields config root must be a mapping"]

    custom_fields = payload.get("custom_fields", [])
    if custom_fields is None:
        custom_fields = []
    if not isinstance(custom_fields, list):
        return [], ["custom_fields must be a list"]

    normalized_fields: List[Dict[str, Any]] = []
    seen_keys = set()

    for index, raw in enumerate(custom_fields):
        if not isinstance(raw, dict):
            warnings.append(f"custom_fields[{index}] is not a mapping and is ignored")
            continue

        item = _normalize_entry(raw)
        key = item["key_name"].lower()
        kind = item["value_kind"]

        if not key:
            warnings.append(f"custom_fields[{index}] missing key_name/key")
            continue
        if key in seen_keys:
            warnings.append(f"custom field '{key}' duplicated and is ignored")
            continue
        seen_keys.add(key)

        if key in PROTECTED_CORE_KEYS:
            warnings.append(f"custom field '{key}' conflicts with protected core field and is ignored")
            continue
        if key in RESERVED_KEYS:
            warnings.append(f"custom field '{key}' conflicts with reserved runtime key and is ignored")
            continue
        if key in PROP_ALIASES or key in LIST_PROP_ALIASES:
            warnings.append(f"custom field '{key}' conflicts with built-in alias and is ignored")
            continue

        if kind not in {"scalar", "enum", "list"}:
            warnings.append(f"custom field '{key}' has unsupported value_kind '{kind}'")
            continue

        if kind == "list":
            item["default_value"] = None

        enum_values = item["enum_values"]
        if kind == "enum":
            if not isinstance(enum_values, list) or not enum_values:
                warnings.append(f"custom enum field '{key}' must define non-empty enum_values/options")
                continue
            normalized_options = [str(v) for v in enum_values if str(v).strip()]
            if not normalized_options:
                warnings.append(f"custom enum field '{key}' has empty enum options")
                continue
            item["enum_values"] = normalized_options
            if item["default_value"] is not None:
                default_str = str(item["default_value"])
                option_map = {opt.lower(): opt for opt in normalized_options}
                if default_str.lower() not in option_map:
                    warnings.append(
                        f"custom enum field '{key}' default_value '{default_str}' not in enum options: {normalized_options}"
                    )
                    continue
                item["default_value"] = option_map[default_str.lower()]
        else:
            item["enum_values"] = []
            if item["default_value"] is not None:
                item["default_value"] = str(item["default_value"])

        item["key_name"] = key
        normalized_fields.append(item)

    return normalized_fields, warnings


def apply_custom_field_definitions(manager: Any, config_path: str) -> List[str]:
    definitions, warnings = load_custom_field_definitions(config_path)
    for definition in definitions:
        ok = manager.upsert_field_definition(
            key_name=definition["key_name"],
            value_kind=definition["value_kind"],
            default_value=definition["default_value"],
            enum_values=definition["enum_values"],
            is_required=definition["is_required"],
        )
        if not ok:
            warnings.append(
                f"failed to register custom field '{definition['key_name']}'"
            )
    return warnings
