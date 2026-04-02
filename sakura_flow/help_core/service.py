from typing import List, Optional

from .catalog import get_help_commands
from .models import HelpCommand
from .renderers import render_cli_help
from ..constants import COMMAND_PREFIX


def get_commands(command_name: Optional[str] = None) -> List[HelpCommand]:
    return get_help_commands(command_name)


def render_cli(command_name: Optional[str] = None) -> str:
    return render_cli_help(get_help_commands(command_name), COMMAND_PREFIX)
