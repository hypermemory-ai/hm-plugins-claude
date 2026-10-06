# HyperMemory enforcement hooks

_Added in plugin 2.12.0 (2026-10-06)._

How we found out why Claude kept failing at HyperMemory, and the two hooks built to stop it.

## 1. The problem

A 2026-10-06 memory quality audit of a heavily used graph scored it **5.7/10**, down from 6.9 on the previous audit. The development work was stored, but in a form nobody could use:

- Descriptions read like build logs. The median was about 940 characters, full of commit hashes and turn numbers.
- Every turn created a new event node, all hanging off one project hub, with no links between related events.
- About a third of the sampled decisions and bugs had no structured data.
- Nothing written was ever reviewed.

## 2. Root cause: Claude follows only enforced rules

The instructions were clear. Claude ignored the ones nothing enforced. Counts from one long Claude Code session of about 322 turns:

| Instruction | Enforced by | What Claude did |
|---|---|---|
| Call `hm_recall` before every answer | Hook reminder on every prompt | 309 calls |
| Load and apply `/hypermemory` before every response | Nothing | **0 loads** |
| Dispatch the memory-writer at the end of **every** turn | Nothing | **134 dispatches**, under half the turns |
| Store new information with `hm_store` / `hm_update` | Nothing | **0 calls** |
| Write memories that make sense to a cold reader | Nothing | Never checked |

Why:

- **The main task wins.** In long coding sessions, memory is the first duty cut when attention runs short.
- **Claude checks that it called a tool, not that the result is good.** A dispatch that happened counted as success, even when what it stored was useless.
- **Context compaction strips the reasons.** What survives a summary is "dispatch the writer", not why it matters.
- **Literal readings excuse skipping.** "Never wait for the writer" became "never check what it wrote".
- **Under challenge, Claude explained instead of owning it,** for example by blaming enrichment and search.

### Why graft always works and HyperMemory didn't

Graft's hooks **do the work themselves**. They run graft and put the results in front of Claude, and the results help with the task at hand. HyperMemory's old hook only printed `MANDATORY: Call hm_recall NOW`, which left the doing to Claude. Writing memories also benefits a future session, not the current one.

**Conclusion:** more prose instructions won't fix this. Enforcement must be mechanical, built from hooks that Claude cannot skip.

## 3. Hook 1: skill injection (`inject-skill.sh`)

**Events**

- `SessionStart`: fires on startup, resume, clear, and after context compaction.
- `UserPromptSubmit`: fires on every message the user sends, before the model sees it.

**How it works**

- A bash script finds `skills/hypermemory/SKILL.md` and prints the whole file to stdout. A header line and an end line wrap the text. If the file is missing it prints a `HYPERMEMORY SKILL MISSING` line instead.
  - The plugin version is passed the plugin's own folder (`${CLAUDE_PLUGIN_ROOT}`).
  - The local copy picks the highest-numbered installed version (`sort -V`) in `~/.claude/plugins/cache/hypermemory-plugins/hypermemory/`.
- For these two events, Claude Code adds the hook's stdout to the model's context for that turn.

**Guarantees**

- The full skill is in Claude's context at session start, after every compaction, and on every prompt.
- Reading it no longer depends on Claude choosing to load it.

**Does not guarantee**

- That Claude follows it. It makes the rules visible; it checks nothing.

**Cost:** about 900 tokens per prompt.

## 4. Hook 2: end-of-turn check (`require-writer.py`)

**Event**

- `Stop`: fires whenever Claude tries to finish a turn.

**How it works**

1. Claude Code passes JSON on stdin that includes `transcript_path`, the session JSONL file.
2. The script finds the start of the current turn: the last message the user actually typed. It skips:
   - tool results;
   - `<task-notification>` background events;
   - compaction summaries (`isCompactSummary`);
   - internal entries (`isMeta`).
3. If that message is the skill's **lightweight skip**, the turn may end. A lightweight skip is 80 characters or fewer and only "hey", "hello", "hi", "howdy", "thanks", "thank you", "okay", "ok" or "got it".
4. Otherwise it scans every assistant entry after that point:
   - for an `Agent` tool call with `subagent_type: "hypermemory:memory-writer"`;
   - for any assistant text after that call.
5. The outcome is one of three:
   - **No dispatch:** it prints `{"decision": "block", "reason": "BLOCKED by the HyperMemory Stop hook: this turn has no hypermemory:memory-writer dispatch. …"}`. Claude Code refuses to stop and hands Claude the reason, so Claude must keep going and dispatch.
   - **Dispatch was the last action:** it blocks with `… Write a closing line after it.`
   - **Both conditions met:** it prints nothing and the turn ends normally.

**Guarantees**

- Claude cannot finish a turn without dispatching the memory-writer and writing a closing line after it.

**Known limits**

- It does not check that `hm_recall` was called before the first text of the turn.
- It does not validate what the dispatch contains, such as a missing `TOKENS:` block or a poor summary. A bad dispatch passes.
- It does not handle Claude Code's `stop_hook_active` flag. If the writer agent were ever unavailable, it would keep blocking rather than let the turn end.
- It has never blocked a live turn. It was tested only by replaying a recorded session transcript:
  - it blocked the audit turn that skipped the writer;
  - it passed a turn that dispatched and closed properly;
  - it passed a bare "ok".

## 5. Where the hooks live

| Copy | Location | Registered in | State |
|---|---|---|---|
| Local (interim) | `~/.claude/hooks/hm-inject-skill.sh`, `~/.claude/hooks/hm-require-writer.py` | `~/.claude/settings.json` (SessionStart, UserPromptSubmit, Stop) | Used on the first test machine until the plugin hooks fire |
| Plugin | `plugins/hypermemory/hooks/inject-skill.sh`, `require-writer.py` in [hm-plugins-claude](https://github.com/hypermemory-ai/hm-plugins-claude) | `plugins/hypermemory/hooks/hooks.json` | Released in plugin **2.12.0**; on the first test machine it was installed and enabled but **not yet firing** after a resumed session |

### Commits

| Repo | Commit | What |
|---|---|---|
| hm-plugins-claude `main` | `8a48db3` | Both hooks, `hooks.json`, README, version 2.11.0 → 2.12.0 |
| hm-plugins-claude `main` | `7ec5881` | Docstring says "the user", not a named person |

### Restart check (2026-10-06)

- `claude plugin list` and `installed_plugins.json` show hypermemory **2.12.0** (git `7ec5881`), user scope, enabled. The injected skill is **0.9.0**.
- The hooks that fired after the restart were the **old 2.11 definitions** (the one-line `MANDATORY…` echo) plus the local copy. The plugin's own `inject-skill.sh` did not fire; its header, `auto-loaded by the HyperMemory plugin hook`, is absent. The resumed session most likely kept the old hook definitions. The other possibility is that the changed hooks need approval in `/hooks`.

## 6. Next steps

1. Fully quit and reopen the Claude app and start a **new** session. Approve the changed hooks in `/hooks` if asked.
2. Check the first prompt for the plugin header `auto-loaded by the HyperMemory plugin hook`. If the skill appears twice, the plugin hooks are live.
3. Once the plugin hooks fire, remove the local copies from `~/.claude/hooks` and `~/.claude/settings.json`, so the skill isn't injected twice.

**Proposed, not built (awaiting decision):**

- Block a turn whose first text came before any `hm_recall` call.
- Block a dispatch whose prompt has no `TOKENS:` block with the required fields.
- Allow the turn to end after a fixed number of consecutive blocks, using `stop_hook_active`, so a missing writer can't trap a session.
- A `UserPromptSubmit` hook that runs `hm_recall` itself and injects the results, the way graft injects its pack.

## 7. Memory-writing rule

Stored in HyperMemory as a mandatory preference:

- Dispatch facts, decisions and lessons, not per-turn progress logs.
- No commit hashes or turn numbers in keys or descriptions; put them in `data.commits`.
- Keep descriptions to 50–300 characters, in plain language.
- Update one node per work item instead of creating a new event every turn.
- Link related events to each other, not only to the project hub.
- Check what was written.
- Never blame enrichment, search or other product features for poor memories.
