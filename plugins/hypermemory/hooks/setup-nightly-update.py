#!/usr/bin/env python3
"""Keep the HyperMemory nightly update task set up on this computer.

Runs on SessionStart with the plugin's folder as its argument:

1. Copies the skill helper (scheduled/hm_skills.py) to
   ~/.claude/hypermemory/hm_skills.py, a path that stays the same across
   plugin versions, so the scheduled task always runs the current helper.
2. When the task hypermemory-nightly-update is not scheduled yet, tells
   Claude to create it with the Claude app's create_scheduled_task tool. A
   hook cannot create the task itself: the schedule lives in the app, and the
   tool is the app's way to add one.
"""

from __future__ import annotations

import sys
from pathlib import Path

TASK_ID = "hypermemory-nightly-update"
TITLE = "HyperMemory nightly update check"
DESCRIPTION = (
    "Every night at midnight, check the HyperMemory plugin for updates, flag a "
    "skill gap, and update installed skills that have newer published versions."
)
CRON = "0 0 * * *"


def main() -> int:
    if len(sys.argv) != 2:
        print("HyperMemory plugin: setup-nightly-update.py needs the plugin folder", file=sys.stderr)
        return 1
    plugin_root = Path(sys.argv[1])
    home = Path.home()
    prompt_file = plugin_root / "scheduled" / f"{TASK_ID}.md"
    helper_source = plugin_root / "scheduled" / "hm_skills.py"
    helper_target = home / ".claude" / "hypermemory" / "hm_skills.py"

    problems: list[str] = []
    try:
        helper = helper_source.read_bytes()
        if not helper_target.is_file() or helper_target.read_bytes() != helper:
            helper_target.parent.mkdir(parents=True, exist_ok=True)
            helper_target.write_bytes(helper)
    except OSError as error:
        problems.append(f"could not install {helper_target}: {error.strerror or error}")

    task_file = home / ".claude" / "scheduled-tasks" / TASK_ID / "SKILL.md"
    if not task_file.is_file():
        if not prompt_file.is_file():
            problems.append(f"the task prompt {prompt_file} is missing from the plugin")
        else:
            print(
                "HyperMemory plugin setup: the nightly update task is not scheduled on this "
                "computer. Before anything else this turn, create it with the "
                "create_scheduled_task tool (Claude app scheduled tasks), with "
                f'taskId "{TASK_ID}", title "{TITLE}", description "{DESCRIPTION}", '
                f'cronExpression "{CRON}", notifyOnCompletion false, and as prompt the full '
                f"text of {prompt_file}, copied exactly. Tell the user in one line that it "
                "is scheduled and runs while the Claude app is open. If the "
                "create_scheduled_task tool is not available in this session (Claude Code "
                "outside the Claude desktop app), tell the user the nightly update could not "
                "be scheduled here and that the next session in the Claude desktop app will "
                "schedule it."
            )
    if problems:
        print("HyperMemory plugin setup problem; tell the user: " + "; ".join(problems))
    return 0


if __name__ == "__main__":
    sys.exit(main())
