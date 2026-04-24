---
name: git-workflow
description: Use when automating git operations including branch creation, commit, push, and pull request creation from agent-driven task completions linked to GitHub Issues
---

# Git Workflow

## Overview

Deterministic protocol for git operations when an agent completes work on a GitHub Issue. Ensures branches are linked, commits are traceable, PRs auto-close issues, and errors are caught before broken code is pushed.

## Scope

**Owns:** Branch naming convention (`feature/issue-N`), commit message format (`feat(#N): Title`), PR creation with issue auto-close (`Closes #N`), error handling for git/gh commands, agent-driven automation of the full branch → PR flow.

**Does not own:** CI/CD pipeline configuration (→ `design-infrastructure`), code review standards (→ `code-quality`), repository or branching strategy design.

**Interfaces with:**
- `design-infrastructure` — CI/CD runs on the branches and PRs this skill creates
- `agentic-development` — agent-driven git automation follows patterns defined here

## When to Use

- **Trigger:** Agent completing development work linked to a GitHub Issue
- **Trigger:** Automating branch → commit → push → PR flow

**Do NOT use for:**
- Manual developer workflows — use standard git flow
- Exploratory branches not tied to an issue

## Core Pattern

```powershell
$IssueNumber = 42
$IssueTitle  = "Add error logging"

$StashResult = git stash 2>&1
$DidStash    = $StashResult -notmatch "No local changes"

try {
    # Branch from latest main
    git checkout main 2>&1 | Out-Null
    git pull origin main 2>&1 | Out-Null
    git checkout -b "feature/issue-$IssueNumber" 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Branch creation failed" }

    # ... make changes ...

    git add . 2>&1 | Out-Null
    git commit -m "feat(#$IssueNumber): $IssueTitle" 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Commit failed" }

    git push origin HEAD 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Push failed" }

    gh pr create `
        --title "feat(#$IssueNumber): $IssueTitle" `
        --body  "Closes #$IssueNumber" `
        --reviewer "ysuurme" 2>&1
    if ($LASTEXITCODE -ne 0) { throw "PR creation failed" }

    gh pr review --comment --body "Agent review notes..." 2>&1
}
finally {
    git checkout main 2>&1 | Out-Null
    if ($DidStash) { git stash pop 2>&1 | Out-Null }
}
```

## Quick Reference

| Step | Command | Why |
|---|---|---|
| Protect local work | `git stash` | Prevents dirty-tree checkout failure |
| Branch | `git checkout -b feature/issue-$N` | Consistent naming, links to issue by convention |
| Pull latest | `git pull origin main` | Always branch from latest main |
| Commit | `git commit -m "feat(#$N): $Title"` | Traceable, machine-parseable |
| Push | `git push origin HEAD` | Name-agnostic — works regardless of branch format |
| PR | `gh pr create --body "Closes #$N"` | Auto-closes issue on merge |
| Self-review | `gh pr review --comment` | Transparent agent notes on the PR |
| Error guard | `$LASTEXITCODE -ne 0` after every command | Prevents pushing broken code |
| Restore | `git stash pop` in `finally` block | Returns developer's local state |

## Implementation

Every `git` and `gh` command MUST be followed by a `$LASTEXITCODE` check. If any step fails, throw and abort — do not continue to the next step.

The `finally` block is not optional. It must restore the developer's stashed work and return to `main` regardless of whether the try block succeeded or failed.

## Common Mistakes

**Skipping `$LASTEXITCODE` checks.**
Every git/gh command requires a check. No exceptions. Silent failures push broken code.

**`git push origin branch-name` with a hardcoded name.**
Always use `git push origin HEAD`. Branch name formats can vary; `HEAD` is always correct.

**PR body without `Closes #N`.**
The PR body MUST contain `Closes #N` on its own line. Additional description is allowed after it, never instead of it.

**Checkout on dirty working tree.**
Always stash before checkout. The `finally` block must pop the stash to restore state.
