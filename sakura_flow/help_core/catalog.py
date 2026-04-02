from typing import List, Optional

from .models import HelpCommand

_COMMANDS: List[HelpCommand] = [
    HelpCommand("list", "[page]", "List tasks", "sakuraflow.help.list", alias="l"),
    HelpCommand("archive", "[page]", "List archived tasks", "sakuraflow.help.archive", alias="ar"),
    HelpCommand("search", "<query>", "Search tasks", "sakuraflow.help.search", alias="find"),
    HelpCommand("add", "<title>", "Add a new task", "sakuraflow.help.add", alias="a"),
    HelpCommand("info", "<id>", "Show task details", "sakuraflow.help.info", alias="i"),
    HelpCommand("note", "<id> <content>", "Add a note", "sakuraflow.help.note", alias="n"),
    HelpCommand("set", "<id> <prop> <value>", "Set task property", "sakuraflow.help.set", alias="s",
                detail_kind="set_props"),
    HelpCommand("append", "<id> <list> <value>", "Append list item", "sakuraflow.help.append", alias="ap",
                detail_kind="list_props"),
    HelpCommand("remove", "<id> <list> <value>", "Remove list item", "sakuraflow.help.remove", alias="rm",
                detail_kind="list_props"),
    HelpCommand("pause", "<id>", "Pause task", "sakuraflow.help.pause"),
    HelpCommand("resume", "<id>", "Resume task", "sakuraflow.help.resume"),
    HelpCommand("complete", "<id>", "Complete task", "sakuraflow.help.complete"),
    HelpCommand("restore", "<id>", "Restore task", "sakuraflow.help.restore"),
    HelpCommand("default_tier", "<tier>", "Set default tier", "sakuraflow.help.set", deprecated=True),
]


def get_help_commands(command_name: Optional[str] = None) -> List[HelpCommand]:
    if command_name is None:
        return list(_COMMANDS)
    target = command_name.strip().lower()
    if not target:
        return list(_COMMANDS)

    matches = []
    for command in _COMMANDS:
        if command.name == target or (command.alias and command.alias == target):
            matches.append(command)
    return matches
