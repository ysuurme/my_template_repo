#Requires -Version 7.0
<#
.SYNOPSIS
    Self-grill subagent CLI — AFK alignment phase probe for the `refine` skill.

.DESCRIPTION
    Thin standalone wrapper around Invoke-Grill (defined in _grill.ps1). Spawns a
    Claude subagent that runs the Grill-Me protocol against one GitHub issue: it
    reads the issue + codebase, generates an Agent Brief, populates open_questions[]
    (and decided_questions[] where it self-resolves from the codebase), and proposes
    glossary diffs.

    Output is structured JSON validated against
    ``src/utils/m_planning.py::GrillResult`` before the orchestrator writes
    anything back.

      Standalone probe (developer machine) — dump the JSON to stdout:
          pwsh .agents/skills/refine/scripts/grill.ps1 -Issue 42
          pwsh .agents/skills/refine/scripts/grill.ps1 -Title T -Body B -DryRun

    The orchestrator does NOT use this wrapper — Orchestrator.psm1 dot-sources
    the library directly (no param() to leak into its scope, see ADR-013).
    This CLI imports the module and calls the same function:
          Import-Module .github/orchestrator/Orchestrator.psd1
          $result = Invoke-Grill -Title $t -Body $b

    The system prompt enforces grill-me Rules 1-4 from refine/SKILL.md:
        1. Codebase first — read before asking
        2. Always recommend — every question carries the agent's position
        3. No branch left open — partial resolution is not resolution
        4. Interface before implementation — no file paths or line numbers

.PARAMETER Issue
    GitHub issue number to grill. Fetches title/body via ``gh issue view``.

.PARAMETER Title
    Issue title for one-shot probes that do not exist on GitHub.

.PARAMETER Body
    Issue body for one-shot probes.

.PARAMETER DryRun
    Render the assembled prompt to stdout without invoking Claude. Useful when
    iterating on the grill-me system prompt itself.

.PARAMETER Model
    Override the Claude model. Defaults to the orchestrator's Opus tier when
    loaded through the module; set KANBAN_MODEL_OPUS or pass -Model explicitly
    for standalone runs.

.PARAMETER MaxTurns
    Maximum agentic turns for the subagent. Defaults to 25 — generous enough
    for codebase exploration but bounded to prevent runaway loops.

.PARAMETER Trace
    Emit { result, tools_called } instead of the bare GrillResult: the tools the
    subagent called, in order. The refine eval (tests/evals) checks Rule 1 with it.

.NOTES
    Tracked in: https://github.com/architecture-that-works/agentic-sdlc/issues/85
    Schema:    src/utils/m_planning.py::GrillResult
    Skill:     .agents/skills/refine/SKILL.md § Unattended invocation pattern
    Library:   .github/orchestrator/lib/Grill.ps1 (Invoke-Grill + helpers) — the module dot-sources it.
#>

[CmdletBinding()]
param(
    [int]   $Issue    = 0,
    [string]$Body     = '',
    [string]$Title    = '(probe)',
    [switch]$DryRun,
    [string]$Model    = '',
    [int]   $MaxTurns = 25,
    [switch]$Trace
)

$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\..\..\..\..\.github\orchestrator\lib\Grill.ps1"

if ($Issue -eq 0 -and (-not $Body)) {
    throw "grill.ps1 requires either -Issue <number> OR -Body <text> (-Title optional). See -? for help."
}

$invokeParams = @{
    Issue    = $Issue
    Body     = $Body
    Title    = $Title
    DryRun   = [bool]$DryRun
    Model    = $Model
    MaxTurns = $MaxTurns
    Trace    = [bool]$Trace
}
$result = Invoke-Grill @invokeParams
if ($DryRun) {
    Write-Output $result.prompt
} else {
    $result | ConvertTo-Json -Depth 10
}
