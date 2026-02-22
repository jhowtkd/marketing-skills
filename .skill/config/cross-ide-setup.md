# Cross-IDE Setup

Goal: run the same methodology in Codex, Kimi Code, and Antigravity with minimal drift.

Language default in this skill is PT-BR with EN-US fallback when requested.

## Portable Standard (Recommended)

Keep one source of truth in Git:

- `skills/compound-growth-os/SKILL.md`
- `skills/compound-growth-os/references/*`
- `skills/compound-growth-os/scripts/*`
- `skills/compound-growth-os/assets/templates/*`

Use plain Markdown + Python so any IDE agent can consume the same workflow.

## Codex

### Project-only usage

Keep the skill in the repository and reference it directly in requests.

### Global usage (all projects)

Create a symlink into your Codex skills home:

```bash
mkdir -p "$HOME/.codex/skills"
ln -sfn \
  "/Users/jhonatan/Repos/mkt-codex/skills/compound-growth-os" \
  "$HOME/.codex/skills/compound-growth-os"
```

Then invoke by name in prompts.

## Kimi Code

Use one of these patterns (depends on current product surface):

1. **Project knowledge / workspace rules**: attach `SKILL.md` + required files in `references/`.
2. **System instruction profile**: paste a slim version of the execution protocol from `SKILL.md` and keep links to local files.

Minimum load set for Kimi:

- `SKILL.md`
- `references/methodology.md`
- `references/build-sequence.md`
- `references/quality-gates.md`

## Antigravity

Use the same portability pattern:

1. Add `SKILL.md` as your base instruction file for the workspace.
2. Keep `references/` in the same project and load selectively by task.
3. Execute local scripts from the terminal when available.

If your Antigravity version supports a dedicated rules or skills directory, point it to this same folder instead of duplicating content.

## Drift Prevention

- Edit only the Git source folder.
- Reuse symlinks/imports in each IDE.
- Avoid creating IDE-specific copies of methodology docs.
- Add version notes to commits when updating process logic.

## Smoke Test Prompt

Run this in each IDE after setup:

```text
Use compound-growth-os.
Create a plan for a [BUSINESS TYPE] from scratch.
Follow Research -> Foundation -> Structure -> Assets -> Iteration.
Show required inputs first, then generate stage outputs and quality gate checks.
```
