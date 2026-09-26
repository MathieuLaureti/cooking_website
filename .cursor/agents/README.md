# Subagent definitions

Canonical system specification: **[`docs/agents-system.md`](../../docs/agents-system.md)**.

Each `*.md` file here is a Cursor subagent for this repository.

| Core (frozen) | `orchestrator`, `github-project`, `planner`, `coder`, `tester`, `documenter` |
| Optional | `project-adoption` — brownfield alignment plans |

Shared skills (gates, PM, delivery, …) live in `~/.cursor/skills/` from [mlaureti-skill-set](https://github.com/MathieuLaureti/mlaureti-skill-set). Repo-specific skills: `.cursor/skills/`.
