# Architecture — Examples

Golden end-to-end session demonstrating the `architect` skill. See [SKILL.md](SKILL.md)
for the quick-start and [REFERENCE.md](REFERENCE.md) for the full metric reference and
step-by-step procedures.

---

## Example 1: Blast-Radius Report for a New Streaming Module

**Context:** The `refine` Agent Brief (see [refine/EXAMPLES.md](../refine/EXAMPLES.md)) has
been signed off. Before opening any implementation file the agent runs `architect` to
compute the blast radius of adding `src/streaming/`.

### Step 1 — Generate dependency graph (output to filesystem only)

```bash
mkdir -p docs/arch

# Write graph to disk — never load the raw file into context
uv run pydeps src --max-bacon=2 --show-deps --no-show > docs/arch/deps.json
```

Extract summary only — this is what enters the context window:

```bash
python -c "
import json
data = json.load(open('docs/arch/deps.json'))
mods = data if isinstance(data, list) else data.get('modules', [])
print(f'Modules: {len(mods)}')
circulars = [m for m in mods if isinstance(m, dict) and m.get('circular')]
print(f'Circular dependencies: {len(circulars)}')
"
```

```
Modules: 2       (src.main, src.config)
Circular dependencies: 0
```

### Step 2 — Identify changed modules

```bash
git diff --name-only HEAD
# → (no commits yet on this branch — new files only)
```

From the Agent Brief, the change adds `src/streaming/` (new bounded context). `src/main.py`
requires a routing addition to wire in the new endpoint.

### Step 3 — Classify affected modules

| Module | Relationship to change | Classification | Reason |
|--------|----------------------|----------------|--------|
| `src/streaming/` | New module | Safe | New bounded context; no existing callers |
| `src/main.py` | Requires routing change | At-risk | Routing table change; test coverage required |
| `src/config.py` | Read-only dependency | Safe | No ownership change; no new config needed |

No layer boundary violations detected. No circular dependencies.

### Step 4 — Module depth check

`src/streaming/` is new — no depth classification yet.

`src/main.py` fan-in: 0 external modules import it (it is the entry point).
Fan-out: 1 (`src.config`). Not a God Object risk.

### Step 5 — Write blast-radius report to disk

```bash
cat > docs/arch/blast-radius.md << 'EOF'
## Blast-Radius Report — SSE Streaming Endpoint

**Changed:** src/streaming/ (new), src/main.py (routing addition)
**At-risk:** src/main.py — routing table change; ensure tests cover the new /stream route
**Safe:** src/config.py — read-only dependency; no ownership change

**Recommendation:** proceed — blast radius is bounded to src/main.py routing only.
No boundary violations detected. No circular dependencies.
EOF
```

### Step 6 — Post as PR comment

```bash
gh pr comment <PR_NUMBER> --body "$(cat docs/arch/blast-radius.md)"
```

### Step 7 — GitHub Issue cross-reference

```bash
gh search issues --repo <owner>/<repo> "streaming SSE" \
  --json number,title,state \
  | jq '.[] | "#\(.number): \(.title) [\(.state)]"'
# → (no overlapping open issues found)
```

### Outcome

Architecture session completes cleanly:

- No circular dependencies.
- `src/main.py` is at-risk but bounded — test coverage gate is sufficient.
- Module Map updated with `streaming | src/streaming/ | src/streaming/ | StreamHandler`.
- Blast-radius report posted as PR comment.

**Next:** `plan` session consumes this report to set scope for issue decomposition.

---

## Example 2: Blocking a Merge Due to Circular Dependency

**Context:** A feature branch modifies `src/utils/m_http.py` to import from
`src/domain/service.py`. A dependency graph reveals a cycle:

```
src.domain.service → src.utils.m_http → src.domain.service
```

**Agent action:**

1. Writes blast-radius report with classification **Blocked**.
2. Posts PR comment:

   ```
   ## Blast-Radius Report — Domain Service Refactor

   **Changed:** src/utils/m_http.py
   **Blocked:** Circular dependency detected:
     src.domain.service → src.utils.m_http → src.domain.service

   **Recommendation:** block — do not merge.
   Fix: move the dependency from src/utils/m_http.py into src/domain/ to break the cycle,
   or extract the shared concern into a new module that neither layer imports transitively.
   ```

3. Writes the fix as an ISSUES.md block — no label; `refine` raises the boundary decision to
   the owner as `human:decision` when it finds one:

   ```
   ISSUE: Break the circular dependency between utils and domain
   ESTIMATE: 3
   PRIORITY: P2
   **Goal**: src/utils/ is generic again and imports nothing from src/domain/.
   **Description**: src.domain.service → src.utils.m_http → src.domain.service. Two valid
   homes for the shared concern exist — a boundary decision.
   **Requirements**:
   1. Move the dependency out of src/utils/m_http.py, or extract the shared concern into a
      module neither layer imports transitively.
   **Acceptance Criteria**:
   - No import cycle; `uv run pytest` passes.
   END_ISSUE
   ```

The PR is not merged until the circular dependency issue is closed.

---

## Example 3: Repo Audit — One Finding, One Issue

**Context:** Asked to "find bloat" in a service repo. Map first: the README says one worker
process per deployment, a nightly job, no concurrent writers — that is the load assumed. Entry
points from the Module Map; the nightly job read fully because it writes data.

The audit reports eleven findings, most important first. One of them:

```
4. **Nightly job re-reads every file every night** (`src/jobs/ingest.py:L40-61`)
   - **Defect:** The job parses every inbox file into the database; nothing marks a file as done.
   - **Case:** After 200 nights it parses 200 nights of files and the run takes 40 minutes; it
     outgrows its nightly window within a year.
   - **Fix:** Skip files already recorded: one query for the set of ingested names, one
     `if name in done: continue`. Four lines.
```

Written as the block `task sync` turns into the issue:

```
ISSUE: Skip already-ingested files in the nightly ingest job
ESTIMATE: 3
PRIORITY: P3
**Goal**: The nightly job's runtime is proportional to new files, not to history.
**Description**: src/jobs/ingest.py:L40-61 parses every inbox file each night; nothing marks a
file as done, so the run grows by one night's files every night (40 minutes after 200 nights).
**Requirements**:
1. Query the set of ingested file names once; skip names already present.
2. One test: a file ingested yesterday is not parsed again tonight.
**Acceptance Criteria**:
- Running the job twice on the same inbox parses each file once.
- `uv run pytest` passes.
END_ISSUE
```

The three small suggestions stay in the report. It ends:

```
Verdict: fix 1 first — a check-then-write race in the upload handler.
Lean: -140 lines, -1 dependency possible.
Not checked: the legacy export module — no caller found anywhere in the tree; listed for
deletion as finding 9.
```
