# HyperMemory AI Plugin for Claude Code

## Overview

This GitHub repository contains the official HyperMemory plugin for Claude Code,
distributed through the `hypermemory-ai` marketplace:

**HyperMemory** (v0.1.0) — Provides persistent cross-conversation memory with
relationship-aware recall, delegated background writes, timeline logging, and
token telemetry. Installs the full protocol skill, hooks for guaranteed
every-turn execution, and a background sub-agent for non-blocking persistence.

## Key Components

### HyperMemory Features

- Hosted OAuth MCP connection to HyperMemory API
- Always-on memory skill (v0.6.6 software-development protocol) with recall and finalization hooks
- Memory-writer sub-agent role for delegated storage, updates, and cleanup
- Accurate token telemetry with weighted activity segmentation
- Relationship-aware hypergraph for personal and cross-session knowledge
- Timeline reporting for chronological session history

### What Gets Installed

| Component | Purpose |
|-----------|---------|
| **MCP Server** | HyperMemory API with OAuth authentication |
| **Skill** | `/hypermemory` — v0.6.6 software-development protocol |
| **Agent** | `memory-writer` — background sub-agent for store/update/token ops |
| **Hooks** | `UserPromptSubmit` forces recall; `Stop` spawns persistence agent |

## Quick Installation

```bash
# One-step install
/install hypermemory-ai/hm-plugins-claude

# Or step by step
/plugin marketplace add hypermemory-ai/hm-plugins-claude
/plugin install hypermemory
```

The MCP server authenticates via OAuth — you'll be prompted to sign in on
first use.

## Architecture Highlights

The plugin uses a two-hook architecture to guarantee memory runs on every turn
without blocking the main agent:

1. **`UserPromptSubmit` hook** — Fires synchronously when the user sends a
   message. Instructs Claude to call `hm_get_overview` (first message only) and
   `hm_recall` with keywords extracted from the user's message. Recalled context
   informs the response.

2. **`Stop` hook** — Fires after Claude finishes responding. Spawns the
   `memory-writer` background agent with a summary of the turn. The agent
   handles `hm_store`, `hm_update`, `hm_forget`, `hm_timeline_write`, and
   `hm_tokens` without blocking the user's next interaction.

## Claude Desktop (MCP Only)

Claude Desktop does not support plugins, hooks, or agents. You can still
connect to HyperMemory via MCP by adding the server configuration in Desktop
settings, but the automatic recall/write lifecycle requires a project-level
`CLAUDE.md` instruction file and operates on a best-effort basis. See
`docs/claude-desktop.md` for setup instructions.

## Data Boundaries

This plugin does not transmit raw source code, complete transcripts, or hidden
reasoning. HyperMemory records structured summaries, relationship-aware nodes,
timeline entries, and token counts.

## Documentation & Support

- [HyperMemory](https://hypermemory.io) — Product homepage
- Security concerns should be reported privately per `SECURITY.md`
- Licensed under MIT
