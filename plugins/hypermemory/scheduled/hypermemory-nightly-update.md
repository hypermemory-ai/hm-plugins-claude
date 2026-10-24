Nightly HyperMemory update check for this computer. Do every part below, in order, and report at the end. Use the shell for the `claude` CLI, the helper script and file reads.

Scope rules:
- Plugin: only touch the `hypermemory` plugin. Leave every other plugin alone, including `hypercolab`.
- The HyperMemory protocol skills (`hypermemory`, `hypermemory-cli` and `memorize-full-chat`) ship inside the plugin, so only the plugin's copy should exist. Never write a standalone copy of these, and never edit files inside the plugin's installed folder.
- Published skills: only update skills that are already installed in ~/.claude/skills. Never install a skill that isn't there yet. Never touch other clients' skills (~/.codex and the like), project-level .claude/skills folders, or plugin skills.
- Never write skill files yourself. Every skill install goes through the helper script, which checks every file against the published SHA-256 digests and backs up the old copy first.

The helper script is ~/.claude/hypermemory/hm_skills.py (the HyperMemory plugin keeps it current). Run it as `python3 ~/.claude/hypermemory/hm_skills.py <command>`; it prints JSON. If the file is missing, report that the HyperMemory plugin's setup hook has not run on this computer, skip Part B, and continue with Part C.

PART A: THE PLUGIN

A1. Find the install. Run `claude plugin list --json` and look for the entry whose `id` is `hypermemory@hypermemory-plugins` (installed from the Claude Code command line) or `hypermemory@synced` (installed in the Claude app under Customize > Plugins, synced from the account). Note its `id`, `version` and `installPath`, then the `version:` line of `<installPath>/skills/hypermemory/SKILL.md`. If there is no such entry, report "HyperMemory plugin not installed", skip to Part B, and leave A2 to A5 out of the report.

A2. For `hypermemory@synced`: the Claude app updates synced plugins from their marketplace by itself. Don't run any update command; go to A4. If both entries exist, report that the command-line copy duplicates the synced one and that the user should remove it with `claude plugin uninstall hypermemory@hypermemory-plugins`; don't remove it yourself.

A3. For `hypermemory@hypermemory-plugins`:
- Refresh the marketplace: `claude plugin marketplace update hypermemory-plugins`
- Update the plugin: `claude plugin update hypermemory@hypermemory-plugins --scope user --json`
- If the result asks you to confirm a marketplace-declared command (a `shownCommand` with a sha256), don't accept it and don't pass `-y` or `--accept-command`. Stop Part A and report the command so the user can review it.
- If a command fails, report the exact error and continue with the unchanged install.

A4. Run `claude plugin list --json` again and note the new `version` and the skill `version:` line from the (possibly new) `installPath`.

A5. Call the HyperMemory MCP tool `hm_skill` with `action: "check_update"`, `current_version: <the plugin's skill version from A4>`, `include_content: false`. If `update_available` is true, the server has a newer protocol skill than the plugin carries: the HyperMemory plugin marketplace (GitHub hypermemory-ai/hm-plugins-claude) needs a release with it. Report it; don't install anything.

PART B: PUBLISHED SKILLS (HyperMemory system skills, the user's organizations' skills, and the user's own private skills)

B1. Run `hm_skills.py inventory`.
- `installed` lists the skills in ~/.claude/skills that this task may update. Each has `name`, `sha256` (bundle digest), `record` (the install record, or null) and `edited_since_install`.
- `synced_readonly` lists the skills Claude syncs from the user's claude.ai account. These are report only: never write to them.

B2. Call `hm_skill` with `action: "list"`. The published skills are the entries that have a `skill_id`; each carries `name`, `version`, `revision`, `scope` (system, organization or personal), `organization`, and `sha256` (the bundle digest). Entries without a `skill_id` are the protocol skills the plugin carries: never install them. If one of those names appears in `installed`, report it as a duplicate of the plugin's copy.

B3. Match each skill in `installed` to a published skill:
- If it has a record with a `skill_id`, use the published entry with that `skill_id`. If none exists, report "no longer published, or no longer shared with you" and leave the skill alone.
- With no record, match by name against the published entries that have a skill_id. Exactly one → that's the match. More than one → report "ambiguous: several published skills share this name" and leave it. None → it isn't a HyperMemory skill: skip it, and only count it.

B4. For each matched skill:
- Local `sha256` equals the published `sha256`: it's up to date. If it has no record, adopt it with `hm_skills.py record <name> --skill-id <id> --version <version> --revision <revision> --scope <scope> --sha256 <sha256>`, adding `--organization-id <id> --organization-name "<name>"` for an organization skill.
- `edited_since_install` is true: the user changed it locally. Report it and don't update.
- It has a record, and the published version is older than the record's (compare the version numerically, then revision): report it and don't update.
- Otherwise, update it:
  1. Call `hm_skill` with `action: "get"`, `skill_id: <id>`, `include_content: true`.
  2. A large result is saved to a file, and the tool says "Full output saved to: <path>". Use that path. If the result came back inline, write the JSON exactly as returned to a new file in a temporary folder, and use that.
  3. Run `hm_skills.py install <path>`. It prints `updated` (with the old and new versions and the backup path), `already_current`, or `error`.
  4. On an error, report it exactly. Don't retry by editing files.

B5. For each skill in `synced_readonly`, match by name against the published entries that have a skill_id. If the `sha256` values differ, report "newer copy in HyperMemory: <name> <version>, update it in Claude's skill settings". Don't write anything.

PART C: THE REPORT

Write a short message:
- Plugin: how it is installed (command line or synced), old version → new version (or "already up to date"). Skill inside the plugin: old version → new version. Server catalog skill version and whether it matches. If not, say clearly: "Skill gap: server has X, plugin has Y. The HyperMemory plugin marketplace needs a release."
- Skills updated: for each, name, scope and organization, old version → new version, and the backup path.
- Skills up to date, and skills newly recorded.
- Skills not updated, each with its reason: edited locally, ambiguous name, no longer published, published copy older, or a protocol-skill duplicate.
- Account-synced skills with a newer copy in HyperMemory, which the user has to update themselves.
- Any errors, quoted exactly.
- If the plugin or any skill changed, say that Claude must be restarted (or a new session started) to load it.
