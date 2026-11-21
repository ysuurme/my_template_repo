#Requires -Version 7.0
<#
.SYNOPSIS
    Self-grill subagent library — exposes Invoke-Grill. Dot-source-safe.

.DESCRIPTION
    Function library for the `refine` skill's AFK alignment phase. Defines
    Invoke-Grill and its helpers with NO top-level param() block, so dot-sourcing
    it (from implement.ps1 / Invoke-Refine, or the grill.ps1 CLI wrapper) only
    registers functions and never pollutes or clobbers the caller's scope
    (see ADR-013). The standalone CLI lives in grill.ps1.

    Rules 1-5 from refine/SKILL.md are enforced by the system prompt below:
        1. Codebase first — read before asking
        2. Always recommend — every question carries the agent's position
        3. No branch left open — partial resolution is not resolution
        4. Interface before implementation — no file paths or line numbers
        5. Smallest complete scope — the core job; everything else goes to out_of_scope

.NOTES
    Tracked in: https://github.com/architecture-that-works/agentic-sdlc/issues/85
    Schema:    src/utils/m_planning.py::GrillResult
    Skill:     .agents/skills/refine/SKILL.md § AFK invocation pattern
#>

# ── Grill-Me system prompt (Rules 1-5 from refine/SKILL.md) ──────────────────

$GrillSystemPrompt = @'
You are the adversarial Senior Architect from the `refine` skill running the
Grill-Me protocol against a single GitHub issue. You operate AFK — there is no
human in this loop. Your job is to surface every alignment risk hidden in the
issue body and resolve as many as you can from the codebase. The remainder
are asked to the issue owner, in the issue, as multiple-choice decisions.

You MUST obey these rules from .agents/skills/refine/SKILL.md:

  Rule 1 — CODEBASE FIRST. If a question can be answered by reading the code,
           read it. Never push a question to a human that the code already
           answers. Decided questions go in `decided_questions[]` with the
           file/symbol evidence summarised in `decision`.
           EXCEPTION: when the issue reserves a choice for the owner — it asks to
           "decide", or says the choice needs the owner's decision — that choice
           is never yours, however clearly the code points one way. Put it in
           `open_questions[]` with your recommendation; the evidence goes there.

  Rule 2 — ALWAYS RECOMMEND, WITH ALTERNATIVES. Every open question carries
           your recommended answer in `decision` ("<option> — because <reason>")
           and exactly two genuine alternatives in `alternatives`, each
           "<option> — <its trade-off>". The owner answers by picking A (the
           recommendation), B or C, or writing their own — so each option must be
           concrete enough to act on without further explanation. A question
           without a recommendation is delegation, not grilling.

  Rule 3 — NO BRANCH LEFT OPEN. Walk every alternative for every decision. If
           you cannot pick between alternatives without human judgement (taste,
           policy, strategy, deadline trade-offs), the question is genuinely
           open and stays in `open_questions[]`.

  Rule 4 — INTERFACE BEFORE IMPLEMENTATION. The Agent Brief describes
           contracts, schemas, and event shapes. NEVER reference file paths,
           module names, or line numbers in the brief — those are volatile.

  Rule 5 — SMALLEST COMPLETE SCOPE. The Agent Brief specifies the smallest
           version that does the core job. Every feature, option or flexibility
           the issue did not ask for goes in `out_of_scope`, one line each — it
           is not built. A vague issue gets the smallest version, not the most
           complete one.

Tooling: you may read CONTEXT.md, AGENTS.md, docs/adr/, .agents/skills/, and
any src/ file. You must not write, edit, or commit anything — your only output
is a single JSON object printed on stdout. No prose, no Markdown fences.

Output schema (must validate against src/utils/m_planning.py::GrillResult):

{
  "agent_brief": {
    "feature_name":      "<short slug>",
    "problem_statement": "<one paragraph, user perspective>",
    "interfaces":        ["<contract 1>", "<contract 2>"],
    "constraints":       ["<ADR-NNN: ...>", "<invariant from CONTEXT.md>"],
    "out_of_scope":      ["<deferred concept>"],
    "tracer_bullet":     "<single narrowest vertical slice>"
  },
  "open_questions": [
    {
      "text":         "<the unresolved alignment question, one sentence>",
      "raised_by":    "self-grill-subagent",
      "decision":     "<recommended option> — because <reason>",
      "alternatives": ["<option B> — <trade-off>", "<option C> — <trade-off>"]
    }
  ],
  "decided_questions": [
    {
      "text":      "<question the codebase answered>",
      "raised_by": "self-grill-subagent",
      "decided_by":"self-grill-subagent",
      "decision":  "<answer> — evidence: <symbol/file summary, no line numbers>"
    }
  ],
  "glossary_diffs": [
    { "term": "<X>", "definition": "<Y>", "disambiguation": "<Z or null>", "action": "add" }
  ]
}

If the issue body is fully specified and the codebase resolves every branch,
return an empty `open_questions[]` — that is the green light for AFK execution.
If even one decision genuinely needs human judgement, that question MUST appear
in `open_questions[]`; the orchestrator asks the owner in the issue and waits.
'@

# ── Helpers ───────────────────────────────────────────────────────────────────

function Get-GrillUserPrompt {
    param([string]$Title, [string]$Body)
    @"
ISSUE TITLE: $Title

ISSUE BODY:
$Body

TASK:
1. Read CONTEXT.md, AGENTS.md, .agents/skills/refine/SKILL.md, the relevant
   ADRs, and the source files implied by the issue body.
2. For every architectural decision the issue raises, decide whether the
   codebase already resolves it. If yes, record it in decided_questions[].
   If no, record it in open_questions[] with your recommended position.
3. Write the Agent Brief in contract terms only — no file paths. Name the
   component the issue is about by its role and public interface (a function
   signature, CLI command, schema or event), never by its source path — even
   when the issue itself names the file.
4. Before printing, scan every agent_brief field for source-code paths
   (src/, tests/, .github/, *.py, *.ps1) and rewrite each one in contract terms.
5. Print the JSON object and nothing else.
"@
}

function Resolve-GrillModel {
    param([string]$Requested)
    if ($Requested) { return $Requested }
    if ($env:KANBAN_MODEL_OPUS) { return $env:KANBAN_MODEL_OPUS }
    if ($KanbanModel_Opus) { return $KanbanModel_Opus }
    # Config.ps1 not loaded (standalone/eval context): read ModelOpus directly from
    # the config file without dot-sourcing it — dot-sourcing runs git operations that
    # are unavailable outside the full module context and would throw.
    $configPath = Join-Path $PSScriptRoot 'Config.ps1'
    $m = Select-String -Path $configPath -Pattern "ModelOpus\s*=\s*'([^']+)'" |
        Select-Object -First 1
    if ($m) { return $m.Matches[0].Groups[1].Value }
    throw "Resolve-GrillModel: cannot determine the Opus model tier — set KANBAN_MODEL_OPUS or verify '$configPath' contains a ModelOpus entry."
}

# Strips Markdown code fences from a Claude response. The subagent is told to
# emit raw JSON but Sonnet occasionally wraps it; trim defensively so the
# pydantic validator never sees fence garbage.
function ConvertFrom-ClaudeJsonResponse {
    param([string]$Raw)
    $text = $Raw.Trim()
    if ($text -match '(?s)```(?:json)?\s*(\{.+\})\s*```') {
        return $Matches[1]
    }
    # Prose around the object ("Here is the result: {...}") — keep the object.
    $first = $text.IndexOf('{'); $last = $text.LastIndexOf('}')
    if ($first -gt 0 -and $last -gt $first) { return $text.Substring($first, $last - $first + 1) }
    return $text
}

# The end of a subagent reply, for an error message that lands in the issue's
# Attempts section: enough to see what went wrong, never the whole transcript.
function Get-GrillOutputTail {
    param([string]$Raw, [int]$MaxChars = 800)
    $text = "$Raw".Trim()
    if (-not $text) { return '(empty output)' }
    if ($text.Length -le $MaxChars) { return $text }
    return '…' + $text.Substring($text.Length - $MaxChars)
}

function Test-GrillResultSchema {
    param([string]$Json)
    # Round-trip through the pydantic model so failures surface as the same
    # ValidationError messages Python callers would see. Returns the normalised
    # JSON on success; throws the last error line plus the answer's tail otherwise.
    $tmpIn  = New-TemporaryFile
    $tmpOut = New-TemporaryFile
    try {
        $Json | Out-File $tmpIn.FullName -Encoding utf8
        $py = @"
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path('src').resolve().parent))
from src.utils.m_planning import GrillResult

data = json.loads(pathlib.Path(r'$($tmpIn.FullName)').read_text(encoding='utf-8'))
result = GrillResult.model_validate(data)
pathlib.Path(r'$($tmpOut.FullName)').write_text(
    result.model_dump_json(by_alias=True), encoding='utf-8'
)
"@
        $err = $py | uv run python - 2>&1 | Out-String
        if ($LASTEXITCODE -ne 0) {
            $why = @($err -split '\r?\n' | Where-Object { $_.Trim() })[-1]
            throw "Self-grill subagent's answer is not a valid GrillResult: $why`n$(Get-GrillOutputTail -Raw $Json)"
        }
        return (Get-Content $tmpOut.FullName -Raw).Trim()
    } finally {
        Remove-Item $tmpIn.FullName, $tmpOut.FullName -ErrorAction SilentlyContinue
    }
}

# ── Public entry point ───────────────────────────────────────────────────────

function Invoke-Grill {
    [CmdletBinding()]
    param(
        [int]   $Issue    = 0,
        [string]$Title    = '',
        [string]$Body     = '',
        [switch]$DryRun,
        [string]$Model    = '',
        [int]   $MaxTurns = 40,  # reading CONTEXT, AGENTS, the skill, ADRs and sources takes turns
        # Also return the tools the subagent called, in order: { result; tools_called }.
        # The refine eval's Tool Correctness metric reads it (#155); refine does not.
        [switch]$Trace
    )

    if ($Issue -gt 0) {
        # Keep stderr out of the parsed string (#270) — merging it via 2>&1 let any
        # incidental gh notice/warning break the strict ConvertFrom-Json below with a
        # cryptic "unexpected character" error instead of a clear one. Same anti-pattern
        # already fixed once for `uv` in Architect.ps1 (#232).
        $errTmp = New-TemporaryFile
        try {
            $issueJson = gh issue view $Issue --json title,body 2> $errTmp.FullName | Out-String
            $exit      = $LASTEXITCODE
            $stderr    = "$(Get-Content $errTmp.FullName -Raw -ErrorAction SilentlyContinue)".Trim()
        } finally {
            Remove-Item $errTmp.FullName -ErrorAction SilentlyContinue
        }
        if ($exit -ne 0 -or -not $issueJson.Trim()) {
            throw "Could not fetch issue #${Issue} via gh (exit $exit): $stderr"
        }
        try {
            $parsed = $issueJson.Trim() | ConvertFrom-Json -ErrorAction Stop
        } catch {
            throw "Issue #${Issue} fetch was not valid JSON: $($issueJson.Trim())$(if ($stderr) { "`nstderr: $stderr" })"
        }
        $Title  = $parsed.title
        $Body   = $parsed.body
    }
    if (-not $Title -or -not $Body) {
        throw "Invoke-Grill requires either -Issue or both -Title and -Body."
    }

    $userPrompt = Get-GrillUserPrompt -Title $Title -Body $Body
    $fullPrompt = "$GrillSystemPrompt`n`n---`n`n$userPrompt"

    if ($DryRun) {
        return [pscustomobject]@{
            mode        = 'dry-run'
            title       = $Title
            body_length = $Body.Length
            prompt      = $fullPrompt
        }
    }

    $resolvedModel = Resolve-GrillModel -Requested $Model

    # The subagent is read-only — restrict tools so it cannot accidentally write
    # to the working tree. The orchestrator alone owns mutations. The result event
    # says how the run ended: a run that stops on its turn budget has no answer, and
    # plain text output would hide that behind an empty or partial reply. stream-json
    # (which needs --verbose) emits one event per line; the assistant events carry
    # the tool calls, the final result event carries the answer.
    $raw = $fullPrompt | claude `
        --model $resolvedModel `
        --allowedTools 'Read,Glob,Grep' `
        --tools        'Read,Glob,Grep' `
        --max-turns   $MaxTurns `
        --output-format stream-json --verbose 2>&1 | Out-String
    $exit = $LASTEXITCODE

    $envelope = $null
    $tools    = [System.Collections.Generic.List[string]]::new()
    foreach ($line in ($raw -split '\r?\n')) {
        if ($line -notmatch '^\s*\{') { continue }
        try { $streamEvent = $line | ConvertFrom-Json -ErrorAction Stop } catch { continue }
        if ($streamEvent.type -eq 'result') { $envelope = $streamEvent }
        elseif ($streamEvent.type -eq 'assistant') {
            foreach ($block in @($streamEvent.message.content)) {
                if ($block.type -eq 'tool_use') { $tools.Add([string]$block.name) }
            }
        }
    }
    if (-not $envelope) {
        throw "Self-grill subagent gave no result (exit code $exit):`n$(Get-GrillOutputTail -Raw $raw)"
    }
    if ($envelope.subtype -ne 'success' -or $envelope.is_error) {
        throw "Self-grill subagent stopped with '$($envelope.subtype)' after $($envelope.num_turns) turn(s) (limit $MaxTurns):`n$(Get-GrillOutputTail -Raw "$($envelope.result)")"
    }

    $validated = Test-GrillResultSchema -Json (ConvertFrom-ClaudeJsonResponse -Raw "$($envelope.result)")
    $result    = $validated | ConvertFrom-Json
    if ($Trace) { return [pscustomobject]@{ result = $result; tools_called = @($tools) } }
    return $result
}
