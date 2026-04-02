from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class HelpCommand:
    """Structured help metadata shared by all frontends.

    Fields:
    - name: Canonical command name (for example "list" or "set").
    - usage: Argument shape shown in help output, without the command prefix.
    - cli_desc: Short plain-text description used by CLI rendering.
    - tr_key: i18n translation key used by rich/front-end renderers.
    - alias: Optional shorthand or alternative command token.
    - detail_kind: Optional renderer hint for richer help sections
      (for example mapping to property/list-property detail blocks).
    - deprecated: Whether the command should be marked as deprecated in help.
    """
    name: str
    usage: str
    cli_desc: str
    tr_key: str
    alias: Optional[str] = None
    detail_kind: Optional[str] = None
    deprecated: bool = False
