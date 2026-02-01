#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Dict, List, Set

VALID_STATUSES = {"pending", "completed"}


def eprint(message: str) -> None:
    print(message, file=sys.stderr)


def load_json(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: str, data: Dict) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=True)
        handle.write("\n")


def validate_graph(data: Dict, path: str) -> List[str]:
    errors: List[str] = []
    if not isinstance(data, dict):
        return [f"{path}: top-level JSON must be an object"]

    project_name = data.get("project_name")
    if not isinstance(project_name, str) or not project_name.strip():
        errors.append(f"{path}: project_name must be a non-empty string")

    tasks = data.get("tasks")
    if not isinstance(tasks, list):
        errors.append(f"{path}: tasks must be a list")
        return errors

    ids: List[str] = []
    ids_seen: Set[str] = set()

    for idx, task in enumerate(tasks):
        if not isinstance(task, dict):
            errors.append(f"{path}: tasks[{idx}] must be an object")
            continue

        task_id = task.get("id")
        if not isinstance(task_id, str) or not task_id.strip():
            errors.append(f"{path}: tasks[{idx}].id must be a non-empty string")
        else:
            if task_id in ids_seen:
                errors.append(f"{path}: duplicate task id '{task_id}'")
            ids_seen.add(task_id)
            ids.append(task_id)

        for field in ("name", "description"):
            value = task.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{path}: tasks[{idx}].{field} must be a non-empty string")

        status = task.get("status")
        if status not in VALID_STATUSES:
            errors.append(
                f"{path}: tasks[{idx}].status must be one of {sorted(VALID_STATUSES)}"
            )

        dependencies = task.get("dependencies")
        if not isinstance(dependencies, list):
            errors.append(f"{path}: tasks[{idx}].dependencies must be a list")
        else:
            for dep in dependencies:
                if not isinstance(dep, str) or not dep.strip():
                    errors.append(
                        f"{path}: tasks[{idx}].dependencies entries must be non-empty strings"
                    )

        for optional_field, expected_type in (
            ("assigned_agent", str),
            ("definition_of_done", str),
        ):
            if optional_field in task:
                value = task.get(optional_field)
                if not isinstance(value, expected_type) or not value.strip():
                    errors.append(
                        f"{path}: tasks[{idx}].{optional_field} must be a non-empty string"
                    )

        for list_field in ("downstream", "hints"):
            if list_field in task:
                value = task.get(list_field)
                if not isinstance(value, list):
                    errors.append(
                        f"{path}: tasks[{idx}].{list_field} must be a list"
                    )
                else:
                    for item in value:
                        if not isinstance(item, str) or not item.strip():
                            errors.append(
                                f"{path}: tasks[{idx}].{list_field} entries must be non-empty strings"
                            )

    task_map: Dict[str, Dict] = {
        task.get("id"): task for task in tasks if isinstance(task, dict)
    }

    for idx, task in enumerate(tasks):
        if not isinstance(task, dict):
            continue
        deps = task.get("dependencies")
        if not isinstance(deps, list):
            continue
        for dep in deps:
            if isinstance(dep, str) and dep not in task_map:
                errors.append(
                    f"{path}: tasks[{idx}].dependencies references missing task id '{dep}'"
                )

    # Cycle detection
    visiting: Set[str] = set()
    visited: Set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visited:
            return
        if task_id in visiting:
            errors.append(f"{path}: dependency cycle detected at '{task_id}'")
            return
        visiting.add(task_id)
        task = task_map.get(task_id)
        if task:
            for dep in task.get("dependencies", []):
                if isinstance(dep, str):
                    visit(dep)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in ids:
        visit(task_id)

    return errors


def collect_dependency_closure(task_map: Dict[str, Dict], root_ids: Set[str]) -> Set[str]:
    closure: Set[str] = set()
    stack: List[str] = list(root_ids)
    while stack:
        task_id = stack.pop()
        task = task_map.get(task_id)
        if not task:
            continue
        for dep in task.get("dependencies", []):
            if dep not in closure:
                closure.add(dep)
                stack.append(dep)
    return closure


def build_keep_set(tasks: List[Dict], keep_downstream: bool) -> Set[str]:
    task_map = {task["id"]: task for task in tasks}
    pending_ids = {task["id"] for task in tasks if task.get("status") == "pending"}
    keep_ids = set(pending_ids)
    keep_ids.update(collect_dependency_closure(task_map, pending_ids))

    if keep_downstream:
        for task in tasks:
            if task.get("status") != "pending":
                continue
            for downstream_id in task.get("downstream", []) or []:
                keep_ids.add(downstream_id)

    return keep_ids


def cmd_validate(args: argparse.Namespace) -> int:
    data = load_json(args.task_graph)
    errors = validate_graph(data, args.task_graph)
    if errors:
        for error in errors:
            eprint(error)
        return 1
    print("OK")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    data = load_json(args.task_graph)
    errors = validate_graph(data, args.task_graph)
    if errors:
        for error in errors:
            eprint(error)
        return 1

    archive_data = None
    archive_tasks: List[Dict] = []
    if os.path.exists(args.archive):
        archive_data = load_json(args.archive)
        archive_errors = validate_graph(archive_data, args.archive)
        if archive_errors:
            for error in archive_errors:
                eprint(error)
            return 1
        archive_tasks = archive_data.get("tasks", [])

    tasks = data.get("tasks", [])
    pending_count = sum(1 for task in tasks if task.get("status") == "pending")
    completed_count = sum(1 for task in tasks if task.get("status") == "completed")
    archived_count = len(archive_tasks)

    print(f"pending: {pending_count}")
    print(f"completed: {completed_count}")
    print(f"archived: {archived_count}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    data = load_json(args.task_graph)
    errors = validate_graph(data, args.task_graph)
    if errors:
        for error in errors:
            eprint(error)
        return 1

    tasks = data.get("tasks", [])
    keep_ids = build_keep_set(tasks, args.keep_downstream)
    kept_tasks = [task for task in tasks if task.get("id") in keep_ids]

    if args.format == "json":
        output = {"project_name": data.get("project_name"), "tasks": kept_tasks}
        print(json.dumps(output, indent=2, ensure_ascii=True))
    else:
        for task in kept_tasks:
            print(f"{task.get('id')}\t{task.get('status')}")
    return 0


def cmd_archive(args: argparse.Namespace) -> int:
    data = load_json(args.task_graph)
    errors = validate_graph(data, args.task_graph)
    if errors:
        for error in errors:
            eprint(error)
        return 1

    if os.path.exists(args.archive):
        archive_data = load_json(args.archive)
        archive_errors = validate_graph(archive_data, args.archive)
        if archive_errors:
            for error in archive_errors:
                eprint(error)
            return 1
    else:
        archive_data = {"project_name": data.get("project_name"), "tasks": []}

    if archive_data.get("project_name") != data.get("project_name"):
        eprint("project_name mismatch between task graph and archive")
        return 1

    tasks = data.get("tasks", [])
    archive_tasks = archive_data.get("tasks", [])

    active_ids = {task.get("id") for task in tasks}
    archive_ids = {task.get("id") for task in archive_tasks}
    overlap = active_ids.intersection(archive_ids)
    if overlap:
        eprint(f"archive contains task ids still in active graph: {sorted(overlap)}")
        return 1

    keep_ids = build_keep_set(tasks, args.keep_downstream)
    to_archive = [
        task
        for task in tasks
        if task.get("status") == "completed" and task.get("id") not in keep_ids
    ]

    if args.dry_run:
        for task in to_archive:
            print(task.get("id"))
        print(f"would archive: {len(to_archive)}")
        return 0

    remaining_tasks = [task for task in tasks if task not in to_archive]
    archive_tasks.extend(to_archive)

    data["tasks"] = remaining_tasks
    archive_data["tasks"] = archive_tasks

    write_json(args.task_graph, data)
    write_json(args.archive, archive_data)

    pending_count = sum(1 for task in remaining_tasks if task.get("status") == "pending")
    completed_count = sum(
        1 for task in remaining_tasks if task.get("status") == "completed"
    )

    print(f"archived: {len(to_archive)}")
    print(f"pending: {pending_count}")
    print(f"completed: {completed_count}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage task_graph.json and archive completed tasks."
    )
    parser.add_argument(
        "--task-graph",
        default=".project_info_for_ai/task_graph.json",
        help="Path to task graph JSON.",
    )
    parser.add_argument(
        "--archive",
        default=".project_info_for_ai/task_graph_archive.json",
        help="Path to task graph archive JSON.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("validate", help="Validate task_graph.json.")

    subparsers.add_parser("stats", help="Show task counts.")

    list_parser = subparsers.add_parser(
        "list", help="List active pending tasks and their dependencies."
    )
    list_parser.add_argument(
        "--format",
        choices=["ids", "json"],
        default="ids",
        help="Output format.",
    )
    list_parser.add_argument(
        "--keep-downstream",
        action="store_true",
        help="Keep completed tasks referenced by pending downstream.",
    )

    archive_parser = subparsers.add_parser(
        "archive", help="Archive completed tasks not required by pending work."
    )
    archive_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show tasks that would be archived without modifying files.",
    )
    archive_parser.add_argument(
        "--keep-downstream",
        action="store_true",
        help="Keep completed tasks referenced by pending downstream.",
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "validate":
        return cmd_validate(args)
    if args.command == "stats":
        return cmd_stats(args)
    if args.command == "list":
        return cmd_list(args)
    if args.command == "archive":
        return cmd_archive(args)

    eprint("Unknown command")
    return 1


if __name__ == "__main__":
    sys.exit(main())
