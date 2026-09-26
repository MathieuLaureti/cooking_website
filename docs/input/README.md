# Input (`docs/input`)

**Owner:** Orchestrator — write only (including during **`/discuss`**; still this folder only).

Start a documentation-only thread with **`/discuss`** — no GitHub issues and no coding until you pass **gate 1** and **gate 2** (see [agents-system.md](../agents-system.md); skills `documentation-mode` and `delegate-routing` in `~/.cursor/skills/`).

Each distinct feature or idea becomes **one markdown file** here. The Orchestrator captures detail and criticism; it does **not** split work into user stories until **github-project** runs after gate 1.

New files default to **Status: parked** for the pipeline; they remain editable in `/discuss`.

**Consumers (read only):** **GitHub Project** agent — when files are `ready-for-github`, invoked by Orchestrator only.

**Naming:** `YYYY-MM-DD-short-slug.md`

**Do not** use this folder for API reference, architecture, or test reports — those live under `docs/` (Documenter).

Return to [documentation hub](../README.md).
