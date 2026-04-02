import argparse
import warnings

from .application import TodoApplication
from .enums import Status
from .help_core import render_cli


def _parse_field_filters(field_args):
    criteria = {}
    if not field_args:
        return criteria, None

    for raw in field_args:
        if "=" not in raw:
            return {}, f"Invalid --field value '{raw}', expected key=value"
        key, val = raw.split("=", 1)
        key = key.strip().lower()
        val = val.strip()
        if not key:
            return {}, f"Invalid --field value '{raw}', key is empty"
        if not val:
            return {}, f"Invalid --field value '{raw}', value is empty"
        criteria[key] = val
    return criteria, None


def register_cli_commands(parser: argparse.ArgumentParser):
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    help_parser = subparsers.add_parser("help", help="Show unified command help")
    help_parser.add_argument("topic", nargs="?", help="Command name or alias")

    # Add
    add_parser = subparsers.add_parser("add", help="Add a new task")
    add_parser.add_argument("title", help="Task title")
    add_parser.add_argument("--creator", default="CLI", help="Creator name")

    # List
    list_parser = subparsers.add_parser("list", help="List tasks")
    list_parser.add_argument("--all", action="store_true", help="Show all tasks including completed ones")
    list_parser.add_argument("--archive", action="store_true", help="Show archived tasks")
    # Search filters
    list_parser.add_argument("--title", help="Filter by title (fuzzy)")
    list_parser.add_argument("--status", help="Filter by status")
    list_parser.add_argument("--tier", help="Filter by tier")
    list_parser.add_argument("--priority", help="Filter by priority")
    list_parser.add_argument("--creator", help="Filter by creator")
    list_parser.add_argument("--collab", help="Filter by collaborator")
    list_parser.add_argument("--label", help="Filter by label")
    list_parser.add_argument("--field", action="append", default=[],
                             help="Filter by custom field, e.g. --field machine_stage=mid")

    # Info
    info_parser = subparsers.add_parser("info", help="Show task details")
    info_parser.add_argument("id", help="Task ID")

    # Set
    set_parser = subparsers.add_parser("set", help="Set task property")
    set_parser.add_argument("id", help="Task ID")
    set_parser.add_argument("prop", help="Property name (title, status, tier, priority, description)")
    set_parser.add_argument("value", help="New value")
    set_parser.add_argument("--editor", default="CLI", help="Editor name")

    # Append
    append_parser = subparsers.add_parser("append", help="Append to list property")
    append_parser.add_argument("id", help="Task ID")
    append_parser.add_argument("list_prop", help="List property name (dependencies, collaborators, labels)")
    append_parser.add_argument("value", help="Value to append")
    append_parser.add_argument("--editor", default="CLI", help="Editor name")

    # Remove
    remove_parser = subparsers.add_parser("remove", help="Remove from list property")
    remove_parser.add_argument("id", help="Task ID")
    remove_parser.add_argument("list_prop", help="List property name")
    remove_parser.add_argument("value", help="Value to remove")
    remove_parser.add_argument("--editor", default="CLI", help="Editor name")

    # Note
    note_parser = subparsers.add_parser("note", help="Add a note to task")
    note_parser.add_argument("id", help="Task ID")
    note_parser.add_argument("content", help="Note content")
    note_parser.add_argument("--author", default="CLI", help="Author name")

    # Status changes
    complete_parser = subparsers.add_parser("complete", help="Mark task as completed")
    complete_parser.add_argument("id", help="Task ID")
    
    pause_parser = subparsers.add_parser("pause", help="Pause task")
    pause_parser.add_argument("id", help="Task ID")
    
    resume_parser = subparsers.add_parser("resume", help="Resume task")
    resume_parser.add_argument("id", help="Task ID")
    
    restore_parser = subparsers.add_parser("restore", help="Restore archived task")
    restore_parser.add_argument("id", help="Task ID")

    # Default Tier
    dt_parser = subparsers.add_parser("default_tier", help="Set default tier (deprecated)")
    dt_parser.add_argument("tier", help="Tier value")


def handle_cli_command(args, service: TodoApplication):
    if args.command == "help":
        print(render_cli(getattr(args, "topic", None)))

    elif args.command == "add":
        task_id = service.add_task(args.title, args.creator)
        print(f"Task created with ID: {task_id}")

    elif args.command == "list":
        # Build criteria
        criteria = {}
        if args.title: criteria['title'] = args.title
        if args.status: criteria['status'] = args.status
        if args.tier: criteria['tier'] = args.tier
        if args.priority: criteria['priority'] = args.priority
        if args.creator: criteria['creator'] = args.creator
        if args.collab: criteria['collaborator'] = args.collab
        if args.label: criteria['label'] = args.label

        custom_criteria, custom_err = _parse_field_filters(getattr(args, "field", []))
        if custom_err:
            print(f"Error: {custom_err}")
            return
        criteria.update(custom_criteria)

        # If criteria exists, use search_tasks
        if criteria:
            tasks = service.search_tasks(criteria)
            # Apply archive/all filter on top of search results if needed?
            # search_tasks currently searches ALL tasks.
            # We should probably filter by status if --all is not present and status is not in criteria.
            
            filtered_tasks = {}
            for tid, task in tasks.items():
                is_done = task['status'] == Status.DONE.value
                if args.archive:
                    if is_done: filtered_tasks[tid] = task
                elif args.all:
                    filtered_tasks[tid] = task
                else:
                    # Default: only show not done
                    if not is_done: filtered_tasks[tid] = task
            
            tasks = filtered_tasks
            
        else:
            # Fallback to original logic
            if args.archive:
                tasks = service.get_archived_tasks()
            else:
                tasks = service.get_tasks(include_done=args.all)
        
        print(f"{'ID':<5} {'Status':<12} {'Title'}")
        print("-" * 40)
        for tid, task in tasks.items():
            print(f"{tid:<5} {task['status']:<12} {task['title']}")

    elif args.command == "info":
        task = service.get_task(args.id)
        if task:
            print(f"ID: {args.id}")
            print(f"Title: {task['title']}")
            print(f"Status: {task['status']}")
            description = task.get('description', '')
            if not description:
                description = "No description"
            print(f"Description: {description}")
            print(f"Tier: {task.get('tier', '')}")
            print(f"Priority: {task.get('priority', '')}")
            print(f"Dependencies: {', '.join(map(str, task.get('dependencies', [])))}")
            print(f"Collaborators: {', '.join(task.get('collaborators', []))}")
            print("Notes:")
            for note in task.get("notes", []):
                print(f"  [{note['time']}] {note['author']}: {note['content']}")
        else:
            print(f"Task {args.id} not found.")

    elif args.command == "set":
        success, val, err = service.set_property(args.id, args.prop, args.value, args.editor)
        if success:
            print(f"Set {args.prop} to {val}")
        else:
            print(f"Error: {err}")

    elif args.command == "append":
        success, err, error_detail = service.append_list_property(args.id, args.list_prop, args.value, args.editor)
        if success:
            print(f"Appended {args.value} to {args.list_prop}")
        else:
            if err == "sakuraflow.msg.self_dependency":
                print(f"Error: self dependency: {args.id}->{args.value}({args.id}->{args.id})")
            elif err == "sakuraflow.msg.circular_dependency" and error_detail:
                print(f"Error: circular dependency: {error_detail}")
            else:
                print(f"Error: {err}")

    elif args.command == "remove":
        success, err = service.remove_list_property(args.id, args.list_prop, args.value, args.editor)
        if success:
            print(f"Removed {args.value} from {args.list_prop}")
        else:
            print(f"Error: {err}")

    elif args.command == "note":
        if service.add_note(args.id, args.content, args.author):
            print("Note added.")
        else:
            print("Failed to add note.")

    elif args.command == "complete":
        if service.update_status(args.id, Status.DONE, "CLI"):
            print(f"Task {args.id} marked as completed.")
        else:
            print(f"Failed to update task {args.id}.")

    elif args.command == "pause":
        if service.update_status(args.id, Status.ON_HOLD, "CLI"):
            print(f"Task {args.id} paused.")
        else:
            print(f"Failed to update task {args.id}.")

    elif args.command == "resume":
        if service.update_status(args.id, Status.IN_PROGRESS, "CLI"):
            print(f"Task {args.id} resumed.")
        else:
            print(f"Failed to update task {args.id}.")

    elif args.command == "restore":
        if service.update_status(args.id, Status.IN_PROGRESS, "CLI"):
            print(f"Task {args.id} restored.")
        else:
            print(f"Failed to update task {args.id}.")
            
    elif args.command == "default_tier":
        warnings.warn(
            "CLI command 'default_tier' is deprecated; use field-definition defaults.",
            DeprecationWarning,
            stacklevel=2,
        )
        if service.set_default_tier(args.tier):
            print(f"Default tier set to {args.tier}")
        else:
            print("Invalid tier.")

    else:
        print("No command specified. Use --help for usage.")
