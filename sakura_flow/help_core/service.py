from typing import List, Optional

from .catalog import get_help_commands
from .models import HelpCommand
from .renderers import render_cli_help
from ..constants import COMMAND_PREFIX


def get_commands(command_name: Optional[str] = None) -> List[HelpCommand]:
    """Get help command definitions for an optional topic.

    Args:
        command_name: Optional command name or alias.

    Returns:
        A list of matching help commands.
    """
    return get_help_commands(command_name)


def render_cli(command_name: Optional[str] = None) -> str:
    """Render CLI help text for an optional topic.

    Args:
        command_name: Optional command name or alias.

    Returns:
        A formatted CLI help string.
    """
    return render_cli_help(get_help_commands(command_name), COMMAND_PREFIX)
