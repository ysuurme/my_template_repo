# Version Control — Reference

Mechanism-level detail for the `version-control` skill. See [SKILL.md](SKILL.md) for the
overview, scope, and quick start. See [EXAMPLES.md](EXAMPLES.md) for worked end-to-end
patterns (feature branch, commit series, worktree-isolated fix).

---

## Branch Naming — Grammar and Rules

### Canonical pattern

```
^feature/\d+-[a-z0-9-]{1,40}$
```

One prefix for every issue-linked branch — a new feature, a bug fix, a docs-only change,
a refactor, a worktree-isolated sub-fix. The branch prefix no longer encodes the kind of
change; the commit type (`feat`, `fix`, `docs`, `refactor`, …) already does that, and the
orchestrator (`Complete-HeldPR`, `Get-CurrentIssueNumber`, the `afk.yml` `pull_request:
closed` trigger) matches on `feature/` alone. A second prefix is a branch the pipeline
cannot see — see [#252](https://github.com/architecture-that-works/agentic-sdlc/issues/252), where a
`fix/`-prefixed PR merged clean but never reconciled its issue's label.

| Segment | Rule | Example |
|---------|------|---------|
| Prefix | Always `feature` | `feature` |
| `/` | Literal separator | `/` |
| Issue number | One or more decimal digits — the GitHub Issue number, no leading zeros | `42` |
| `-` | Literal separator after the issue number | `-` |
| Slug | 1–40 lowercase alphanumeric characters and hyphens; 2–4 words; no trailing hyphen | `user-auth-endpoint` |

**Slug rules:**
- Lowercase only — no uppercase, no underscores.
- Hyphens between words, not spaces.
- Maximum 4 words. Shorter is better — slugs are navigation, not description.
- Derived from the issue title: drop articles and prepositions, take the 2–4 most significant nouns/verbs.
- The slug does not need to match the commit type — `feature/17-order-rounding` fixing a
  bug is correct; the commit message's `fix(orders): ...` carries the "this is a fix"
  signal, not the branch name.

### `Get-CurrentIssueNumber` parse contract

The orchestrator's `implement.ps1` uses `Get-CurrentIssueNumber` to extract the issue number
from the branch name. This function expects the branch to start with `feature/` followed
immediately by the issue number and a `-`. Any branch that does not satisfy the regex above
will cause `Get-CurrentIssueNumber` to return `$null`, breaking the kanban pipeline.

```powershell
# How the parse works (simplified):
$branch = git rev-parse --abbrev-ref HEAD
if ($branch -match '^feature/(\d+)-') { $issueNumber = $Matches[1] }
```

Always verify the branch name satisfies the regex before pushing.

---

## Conventional Commit Format — Full Specification

### Template

```
<type>(<scope>): <short description>

[optional body]

Closes #<issue-number>
```

### Type × scope matrix

| Type | When to use | Example scope |
|------|-------------|---------------|
| `feat` | New user-visible behaviour | `orders`, `auth`, `api` |
| `fix` | Corrects a defect in existing behaviour | `orders`, `pipeline` |
| `refactor` | Internal restructuring, no behaviour change | `utils`, `config` |
| `test` | Adds or modifies tests only — no production code change | `orders`, `auth` |
| `docs` | Documentation, comments, README only | `adr`, `readme` |
| `chore` | Tooling, dependencies, CI configuration | `deps`, `ci` |

**Scope rules:**
- Use the module or domain area that owns the change: `orders`, `auth`, `pipeline`, etc.
- Match the `src/<domain>/` directory name where possible.
- Omit scope only for repository-wide changes (e.g. `chore: bump Python to 3.13`).
- Scope is always lowercase and unquoted inside the parentheses.

**Short description rules:**
- Imperative mood: "add", "fix", "remove" — not "added", "fixing", "removes".
- No capital letter at the start.
- No period at the end.
- 72 characters maximum.

**Body rules:**
- Explain WHY, not WHAT. The diff shows what changed; the body explains the motivation.
- Blank line between short description and body — required by Git's commit-message parser.
- Wrap at 72 characters.
- Optional. Omit if the short description is sufficient.

### `Closes #N` placement rules

`Closes #N` triggers GitHub's auto-close on merge. Placement rules:

1. **Final commit only.** Only the last commit before PR creation carries `Closes #N`. Intermediate commits in a multi-commit branch do not include it.
2. **Exact keyword.** GitHub recognises `Closes`, `Fixes`, `Resolves` (case-insensitive). Use `Closes` for consistency.
3. **Blank line before `Closes #N`.** It must be separated from the body (or description) by a blank line, or it will not be parsed.
4. **PR body also carries `Closes #N`.** This is the safe duplicate — if the commit message is edited during squash, the PR body ensures the issue closes.

### Squash-merge implications

This project merges via squash only (enforced by `ship`). Under squash merge:
- All individual commits collapse into one commit on `main`.
- The squash commit message is derived from the PR title and body — not from individual commit messages.
- Individual commit messages are visible in the branch history but disappear from `main`'s log after merge.

Consequence: `Closes #N` in individual commit messages is not visible after merge. The PR body
`Closes #N` is the effective auto-close trigger. Always include it in both.

---

## PR Creation — Flag Reference

Full `gh pr create` flag reference for this project's conventions:

```bash
gh pr create \
  --title "<type>(<scope>): <short description>" \
  --body "## Summary
- <bullet 1>
- <bullet 2>

## Closes
Closes #<issue-number>" \
  --base main
```

| Flag | Purpose | Rule |
|------|---------|------|
| `--title` | PR title — shown in GitHub UI and squash commit message | Must match conventional-commit format (same as commit subject) |
| `--body` | PR description | Must contain `Closes #N`; use `## Summary` section for bullet points |
| `--base` | Target branch for merge | Always `main` — direct PRs to feature branches are not permitted |
| `--draft` | Mark PR as draft | Use when the branch is not yet ready for review but review feedback is needed early |
| `--reviewer` | Request a reviewer by GitHub username | Optional; only for human-reviewed PRs |

**Body template rationale:**
- `## Summary` provides the agent or reviewer with a structured change description.
- `## Closes` isolates the auto-close keyword so it is never accidentally omitted during editing.

---

## Worktree Lifecycle

### When to use a worktree

Use `git worktree` when:
- The review auto-fix loop needs to work in an isolated branch without discarding uncommitted changes on the current branch.
- A hotfix must be developed alongside an in-progress feature branch.
- The CI/CD environment runs multiple branches simultaneously.

Do NOT use `git worktree` for routine feature work — one branch, one checkout is sufficient.

### Full lifecycle

```bash
# 1. Add — creates the worktree at a sibling path. The branch is still feature/<n>-<slug>
#    (same issue number as the branch it isolates from, different slug) — the orchestrator
#    only ever matches feature/, so a worktree branch is no exception.
git worktree add ../fix-<description> -b feature/<issue-number>-<slug>

# 2. Work — navigate to the worktree and make changes
cd ../fix-<description>
# ... implement, test, commit ...

# 3. Push — push the worktree branch like any branch
git push -u origin feature/<issue-number>-<slug>

# 4. Remove — clean up after merge or abandonment
cd <project-root>
git worktree remove ../fix-<description>
```

### Stale-worktree detection

A stale worktree is a `git worktree` entry that points to a path that no longer exists on disk.

```bash
# List all worktrees (shows path, branch, HEAD)
git worktree list

# Prune stale worktree references (safe, idempotent)
git worktree prune

# Verify after pruning
git worktree list
```

Run `git worktree prune` whenever `git worktree list` shows a path marked as `(bare)` or
`(prunable)`. Stale worktrees do not affect the working tree but they clutter `git worktree list`
output and can confuse tooling.

### Naming convention for worktree directories

Worktree directories live at the same level as the project root (sibling, not child):

```
parent/
  my-project/          ← project root (main worktree)
  fix-branch-42-slug/  ← fix worktree (sibling)
```

Never place a worktree inside the project root — it will be picked up by `git status` and
interfere with test discovery.
