---
name: hypercolab
description: Coordinate work in a HyperColab-enabled Git repository. Join and sync before planning, claim paths before edits, respect other agents' ownership, and record meaningful project activity.
---

# HyperColab

Use this skill whenever the current Git repository resolves to a HyperColab project.

1. Call `hm_colab_join` at the start of a coding session, then read the returned brief.
2. Call `hm_colab_sync` before accepting or decomposing work.
3. Call `hm_colab_claim` for planned directories or file sets. File edits may auto-claim a free file through the hook.
4. Treat `do_not_touch` paths as blocked. Coordinate or request a handoff instead of bypassing a conflict.
5. Call `hm_colab_update` when the plan, rationale, scope, status, or blocker changes.
6. Use `hm_colab_activity` for architectural choices, rejected alternatives, discoveries, test results, or release activity.
7. Call `hm_colab_finish` before stopping completed, released, abandoned, or handed-off work.

Two further tools answer questions without changing anything:

- `hm_colab_resolve` maps a repository remote URL to a project **without
  joining**. Use it to find out whether a repository is a HyperColab project
  at all, before step 1 commits the session to it.
- `hm_colab_timeline` queries recorded project history, filtered by actor,
  kind, branch, path, or full-text search. Use it to answer "what happened
  here, and who did it" — `hm_colab_sync` reports the current state, not the
  history behind it.

`hm_colab_check` is called for you by the `PreToolUse` hook before each write.
Call it directly only when planning a change set you have not started editing.

For work where timeline maintenance would distract the implementation agent,
delegate one bounded coordination writer and wait for it. Follow
[references/coordination-agent.md](references/coordination-agent.md). Keep
`hm_colab_join`, `hm_colab_sync`, and path claims on the main agent because their
results directly affect planning and write safety.

Never put hidden reasoning, secrets, raw source contents, or full command output in timeline summaries.

