# Automation Approval Strategy

Use this file when the goal is to reduce repeated approvals while keeping the workflow controlled.

## Default rule for this skill

Treat the workflow itself as fully automated.
Only require approval when the agent must execute a host-level file, script, or shell command on the local machine.

That means:
- workflow coordination should be automatic
- artifact creation and state transitions should be automatic
- approvals should be reserved for actual local execution actions

## Strategy A: relax exec approval mode

Primary objective:
- reduce repeated approvals for low-risk workflow support commands
- keep high-risk or system-wide commands behind approval

## What should stay tool-first

Prefer these tools before any shell command:
- `read`
- `write`
- `edit`
- `sessions_spawn` in `mode="run"`
- `sessions_send`

Reason:
- these tools are better aligned with the workflow
- they usually avoid repeated exec approvals
- they keep the pipeline artifact-oriented

## What exec is still used for

Exec should be treated as a support layer, not the core workflow layer.

Typical remaining exec use cases:
- `git status`
- `git add`
- `git commit`
- fixed workspace-local Python export scripts
- copying the skill from the workspace into the OpenClaw skill folder
- safe workspace-local searches when first-class tools are insufficient

## Recommended policy shape

### Tier 1 — no approval required
Allow the workflow to proceed automatically through:
- file reads/writes/edits
- run-mode subagent dispatch
- local evaluation and artifact generation

### Tier 2 — allowlisted low-risk exec
Reduce repeated approval prompts for these narrowly scoped patterns:
- git commands inside the workspace only
- fixed Python scripts inside the workspace only
- copying from the workspace skill folder into the OpenClaw skill folder
- read-only searches scoped to the workspace

### Tier 3 — still require approval
Keep approval for:
- destructive file operations
- unknown or broad shell commands
- commands outside the workspace without a clear reason
- package installs or environment changes
- network-sensitive or system-wide operations

## Project-specific recommendation

For the WorldQuant 5-agent workflow, the best automation gain comes from making the workflow body non-exec and only relaxing exec for publishing and maintenance actions.

That means:
- the coordinator uses run-mode subagents for stage execution
- artifacts are passed through files
- exec is mostly limited to publication, versioning, and optional exports

## Desired end state

A practical end state is:
- no approval needed for normal run-mode workflow execution
- fewer approvals for git/export/copy maintenance commands
- approvals still required for risky system changes

## Why this matters

Without this strategy, the workflow may be technically correct but operationally annoying. Repeated approvals slow down iteration, especially when publishing new skill revisions or exporting documentation.
