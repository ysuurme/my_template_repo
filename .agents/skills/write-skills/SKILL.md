---
name: write-skills
description: Use when creating new skills, editing existing skills, splitting an overgrown skill, or validating a skill before deployment
---

# Writing Skills for Agents

## Overview

A **skill** is a constraint document for AI agents — a reference that prevents hallucinated approaches by encoding proven patterns and hard rules. Skills are reusable across projects and sessions.

**Skills are:** Proven techniques, hard constraints, patterns, tool references.
**Skills are NOT:** Project-specific conventions, one-off solutions, or rules enforceable by a script or linter.

## Scope

**Owns:** Skill creation standards, SKILL.md template, validation process, MECE enforcement, routing signal format, update and split guidance, ASO rules.

**Does not own:** Project-specific agent instructions (→ `CLAUDE.md` / `AGENT.md`), individual skill content, validation scripts.

**Interfaces with:** All other skills — this skill defines the contract every other skill must follow.

## When to Use

- Creating a new skill
- Editing or adding constraints to an existing skill
- Detecting whether a skill needs splitting (scope creep check)
- Validating a skill before deploying it

**Do NOT create a skill for:**
- Project-specific conventions — use `CLAUDE.md` or `AGENT.md`
- One-off solutions that won't recur across projects
- Rules enforceable by a linter, hook, or script

## Core Pattern

### The Iron Law

**No skill without a failing baseline first.** Applies to new skills AND edits.

1. Run the pressure scenario — verify the agent gets it wrong
2. Document the exact rationalizations used — these become your constraints
3. Write the skill closing those specific loopholes
4. Verify compliance

Write skill before baseline? Delete it. Start over. No exceptions: don't keep it as "reference," don't adapt it while writing. Delete means delete.

**Closing loopholes:** State the rule AND forbid the specific workaround. A rule without a closed escape route will be rationalized away.

### The MECE Law

Every skill must be mutually exclusive and collectively exhaustive within the skill system.

- **Mutually exclusive:** No `Owns` entry in one skill duplicates an `Owns` entry in another
- **Collectively exhaustive:** Every concern in the domain has exactly one skill that owns it

**MECE alarm — flag immediately when:**
- A new `Owns` entry already appears in another skill's Scope → resolve overlap before writing
- A constraint needs qualifying "except when X" more than twice → split signal
- Only half the skill is relevant for the task at hand → split signal
- A new independent trigger condition is being added to an existing skill → split signal

When a MECE alarm fires, stop and resolve it before continuing. Do not write around it.

## Quick Reference

### Frontmatter Rules

```yaml
---
name: skill-name-with-hyphens       # letters, numbers, hyphens only
description: Use when [triggering conditions only — never summarize the workflow]
---
```

Description = triggering conditions only. Summarizing the workflow lets the agent shortcut the skill body.

```yaml
# ❌ Summarizes workflow — agent skips the skill body
description: Use when executing plans — dispatches tool calls with code review between tasks

# ✅ Triggering conditions only — agent reads the skill
description: Use when executing implementation plans with independent tasks in the current session
```

### Checklists

**Create:**
1. Run baseline — verify agent fails, document exact failure modes
2. Write frontmatter (`name`, `description` — triggering conditions only)
3. Write Scope block (`Owns`, `Does not own`, `Interfaces with`)
4. Write constraints closing the specific loopholes from step 1 only
5. Validate — agent re-attempts scenario, verify compliance
6. New loophole found → return to step 1 for that loophole

**Update:**
1. Run baseline — verify agent fails with the current skill
2. Check MECE alarm conditions — does the fix expand scope or trigger a split?
3. Add constraints closing the specific gap
4. Validate — passes new scenario AND all previous scenarios

**Split:**
1. Confirm two independent scopes — each must have its own standalone trigger
2. Create two new skills with `Interfaces with` cross-references to each other
3. Distribute existing content — no duplication allowed
4. Delete the original skill
5. Update all skills that referenced the original

### File Structure

```
.agents/skills/
  skill-name/
    SKILL.md              # Required
    supporting-file.*     # Only if needed
```

Keep inline: principles, patterns under 50 lines, bulleted plans.
Move out: large reference tables, scripts, anything over 50 lines.

## Implementation

### SKILL.md Template

```markdown
---
name: skill-name-with-hyphens
description: Use when [triggering conditions only]
---

# Skill Name

## Overview
Core principle in 1-2 sentences. What problem does this skill prevent?

## Scope
**Owns:** What this skill is solely responsible for.
**Does not own:** What explicitly falls outside (→ `other-skill`).
**Interfaces with:** `other-skill` — what the handoff is and why.

## When to Use
- **Trigger:** Specific symptom or situation.
- **Do NOT use for:** Explicit exclusions (→ `other-skill`).

## Core Pattern
The key constraint or technique with a before/after example.

## Quick Reference
Table or bullets for scanning during active work.

## Implementation
Inline code < 50 lines, or link to supporting file.

## Common Mistakes
What the agent gets wrong without this skill + the fix.
```

### Routing Signals

Routing signals are pointers inside skill content that direct an agent to the correct skill for a given concern. They are not documentation — agents follow them actively.

**Format:** `→ \`skill-name\``

**Usage rules:**
- Every `Does not own` entry MUST have a `→ skill-name` pointer
- Every `Do NOT use for` exclusion MUST have a `→ skill-name` pointer
- Mandatory pre-reads use: `**REQUIRED:** See → \`skill-name\``
- Never leave a gap without a pointer — "not here" without "go there" is an agent dead end

**In practice:**
```markdown
**Does not own:** Model serving (→ `mlops`), feature pipeline implementation (→ `data-engineering`).
**Do NOT use for:** Production deployment (→ `mlops`).
**REQUIRED:** See → `design-system` before defining bounded contexts.
```

### Agent Search Optimization (ASO)

Agents select which skill to read from the `description` field alone.

1. **Description = when to use, not what the skill does** — see frontmatter rules
2. **Keyword coverage** — use words the agent would search for: error messages, synonyms, exact command names as they appear in the agent's context
3. **Token efficiency** — dense and direct; no motivational text, no repeated explanations; move large reference material to supporting files
4. **Naming** — action/insight-oriented: `condition-based-waiting` not `async-helpers`

## Common Mistakes

**Writing skill before baseline.**
Delete it. Start over. The baseline defines what the skill must prevent — without it the constraints are guesses.

**Description summarizes workflow instead of trigger.**
Ask: "does this tell the agent WHEN to use the skill, or WHAT it does?" Rewrite if the latter.

**`Does not own` entries without routing pointers.**
Every exclusion must name where that concern lives. "Not here" without "go there" is a dead end.

**Scope too broad** ("Owns: everything in this domain").
Scope must be specific enough that a second skill in the same domain has a non-overlapping `Owns` list.

**Scope creep on update — new content added without checking MECE.**
Re-read the Scope block before every update. If new content doesn't fit in `Owns`, update Scope explicitly or route to the correct skill. If it triggers a MECE alarm, stop and split.
