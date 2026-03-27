import argparse
import os

from sakura_flow.application import TodoApplication
from sakura_flow.cli_entry import register_cli_commands, handle_cli_command
from sakura_flow.manager import TodoManager


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

    data_dir = os.path.join(mcdr_root, 'sf_tasks')
    data_path = os.path.join(data_dir, 'tasks.db')
    legacy_json_path = os.path.join(data_dir, 'tasks.json')

    # Initialize backend service
    manager = TodoManager(data_path, legacy_json_path=legacy_json_path)
    if manager.startup_warning:
        print(f"[WARN] {manager.startup_warning}")
    service = TodoApplication(manager)

    handle_cli_command(args, service)

if __name__ == "__main__":
    main()
