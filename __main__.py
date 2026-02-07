import argparse
import os
import sys
from sakura_flow.manager import TodoManager
from sakura_flow.controller import TodoController
from sakura_flow.cli_entry import register_cli_commands, handle_cli_command

def main():
    parser = argparse.ArgumentParser(description="Sakura Flow CLI")
    register_cli_commands(parser)

    args = parser.parse_args()

    # Determine data path logic
    cwd = os.getcwd()
    
    # Strategy: Try to find MCDR root relative to current location
    # Priority 1: If running inside plugin source folder (contains mcdreforged.plugin.json)
    if os.path.exists(os.path.join(cwd, "mcdreforged.plugin.json")):
        mcdr_root = os.path.abspath(os.path.join(cwd, "../.."))
    # Priority 2: If running in a directory that contains .pyz file (e.g. plugins dir)
    elif os.path.exists(os.path.join(cwd, "../sf_tasks")):
        mcdr_root = os.path.abspath(os.path.join(cwd, ".."))
    # Priority 3: Fallback to current directory (assuming running from MCDR root)
    else:
        # If sf_tasks exists in ../.., use it
        if os.path.exists(os.path.join(cwd, "../../sf_tasks")):
             mcdr_root = os.path.abspath(os.path.join(cwd, "../.."))
        else:
             # If we really can't find it, assume we are in plugin folder as requested
             mcdr_root = os.path.abspath(os.path.join(cwd, "../.."))

    data_path = os.path.join(mcdr_root, 'sf_tasks', 'tasks.json')
    
    # Initialize manager and controller
    manager = TodoManager(data_path)
    controller = TodoController(manager)

    handle_cli_command(args, controller)

if __name__ == "__main__":
    main()
