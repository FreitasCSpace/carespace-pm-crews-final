#!/usr/bin/env python3
"""Standalone dedup tool — run directly to clean up duplicate tasks.

Usage:
    python dedup.py              # dry run — shows what would be deleted
    python dedup.py --execute    # actually deletes duplicates

Requires CLICKUP_API_TOKEN or CLICKUP_PERSONAL_TOKEN env var.
"""
import os, sys, json, re, time
from collections import defaultdict

# Reuse the ClickUp API helper
sys.path.insert(0, os.path.dirname(__file__))


def _clickup_api(endpoint, method="GET", payload=None):
    import urllib.request
    token = os.environ.get("CLICKUP_PERSONAL_TOKEN",
            os.environ.get("CLICKUP_API_TOKEN", ""))
    if not token:
        print("ERROR: Set CLICKUP_API_TOKEN or CLICKUP_PERSONAL_TOKEN")
        sys.exit(1)
    url = f"https://api.clickup.com/api/v2/{endpoint}"
    headers = {"Authorization": token, "Content-Type": "application/json"}
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def main():
    from shared.config.context import L
    dry_run = "--execute" not in sys.argv
    backlog_id = L["master_backlog"]

    print(f"\n  Dedup Backlog Cleanup {'(DRY RUN)' if dry_run else '(EXECUTING)'}")
    print("  " + "=" * 50)

    # Load all tasks (paginated)
    all_tasks = []
    page = 0
    while True:
        data = _clickup_api(f"list/{backlog_id}/task?archived=false&page={page}")
        tasks = data.get("tasks", [])
        if not tasks:
            break
        all_tasks.extend(tasks)
        print(f"  Loaded page {page}: {len(tasks)} tasks (total: {len(all_tasks)})")
        if len(tasks) < 100:
            break
        page += 1

    print(f"\n  Total tasks in backlog: {len(all_tasks)}")

    # Group by identifier
    groups = defaultdict(list)
    for t in all_tasks:
        name = t["name"]
        match = re.search(r'\(([^)]*#\d+)\)\s*$', name)
        if match:
            key = match.group(1).lower()
        else:
            key = re.sub(r'\s+', ' ', name.lower().strip())
        groups[key].append({
            "id": t["id"],
            "name": t["name"],
            "date_created": t.get("date_created", "0"),
        })

    # Find duplicates
    total_dupes = 0
    total_groups = 0
    for key, task_group in sorted(groups.items()):
        if len(task_group) <= 1:
            continue
        total_groups += 1
        task_group.sort(key=lambda x: x["date_created"])
        keep = task_group[0]
        dupes = task_group[1:]
        total_dupes += len(dupes)

        print(f"\n  DUPLICATE GROUP: {key} ({len(task_group)} copies)")
        print(f"    KEEP:   {keep['name'][:70]} ({keep['id']})")
        for d in dupes:
            if dry_run:
                print(f"    DELETE: {d['name'][:70]} ({d['id']})")
            else:
                try:
                    _clickup_api(f"task/{d['id']}", method="DELETE")
                    print(f"    DELETED: {d['name'][:70]} ({d['id']})")
                    time.sleep(0.2)
                except Exception as e:
                    print(f"    ERROR:  {d['name'][:70]} — {e}")

    print(f"\n  " + "-" * 50)
    print(f"  Duplicate groups: {total_groups}")
    print(f"  Total duplicates: {total_dupes}")
    if dry_run:
        print(f"  Action: DRY RUN — nothing deleted")
        print(f"  To delete, run: python dedup.py --execute")
    else:
        print(f"  Action: {total_dupes} tasks deleted")
    print()


if __name__ == "__main__":
    main()
