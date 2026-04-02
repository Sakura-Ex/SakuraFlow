from typing import List

from .models import HelpCommand


def render_cli_help(commands: List[HelpCommand], command_prefix: str) -> str:
    """Render a plain-text CLI help page.

    Args:
        commands: Help command definitions to render.
        command_prefix: Command prefix to display in examples.

    Returns:
        A formatted help string.
    """
    if not commands:
        return "No help topic found."

    lines = ["Sakura Flow commands:", ""]
    for command in commands:
        usage = f" {command.usage}" if command.usage else ""
        alias = f" (alias: {command.alias})" if command.alias else ""
        deprecated = " [deprecated]" if command.deprecated else ""
        lines.append(f"{command.name}{alias}{deprecated}")
        lines.append(f"  CLI: {command.name}{usage}")
        lines.append(f"  MCDR: {command_prefix} {command.name}{usage}")
        lines.append(f"  {command.cli_desc}")
        lines.append("")
    return "\n".join(lines).rstrip()
