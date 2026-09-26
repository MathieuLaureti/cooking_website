# Work manifest (`docs/work/`)

**`active-slice.yaml`** — single source of truth for the active agent-managed slice: input doc path, issue numbers, branch, PR URL, delivery report path.

Copy **`active-slice.template.yaml`** to **`active-slice.yaml`** when gate 2 starts a slice (usually after **github-project** creates issues).

**Skill:** `agent-work-manifest` in `~/.cursor/skills/agent-work-manifest/`.

Only GitHub issues labeled **`agent-managed`** and listed in the manifest are in scope for coder / tester / documenter.

Return to [documentation hub](../README.md).
