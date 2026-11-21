"""Tests for the issue-as-interface loop: decisions asked and answered in the issue,
the attempt budget, and the helpers they rest on.

- stages/Refine.ps1 — Invoke-AnswerCheck judges the owner's reply against the open
  questions; Request-Decisions asks in the issue.
- lib/GitHub.ps1 — Add-Comment's 🤖/· prefix guard, Set-DecisionSection,
  Add-FailedAttempt / Set-AttemptsSection, Add-IssueToBoard.
- Orchestrator.psm1 — the refine path's routing, and the implement path's attempt
  loop (retry with the failure in context, agent:failed only after MaxRetries).

gh, claude and the carrier helpers are replaced by in-memory fakes at module script
scope, so nothing touches GitHub. Conductor tests run in tmp_path because the
conductor's finally block resets git.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

PWSH = shutil.which("pwsh") or "pwsh"
REPO_ROOT = Path(__file__).parent.parent.parent
MODULE = REPO_ROOT / ".github" / "orchestrator" / "Orchestrator.psd1"

pytestmark = pytest.mark.skipif(not shutil.which("pwsh"), reason="pwsh not available")


def _run(body: str, cwd: Path | None = None) -> dict:
    """Run `body` inside the module's session state; it must print one JSON line last."""
    script = (
        "$env:GITHUB_REPOSITORY = 'octocat/sandbox'\n"
        "$env:GITHUB_DEFAULT_BRANCH = 'main'\n"
        f"Import-Module '{MODULE}' -Force -DisableNameChecking\n"
        "& (Get-Module Orchestrator) {\n"
        "function script:Write-Log { param($Message, $Color) }\n"
        f"{body}\n"
        "}\n"
    )
    result = subprocess.run(
        [PWSH, "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else None,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    lines = [line for line in result.stdout.splitlines() if line.startswith("{")]
    assert lines, f"no JSON output:\n{result.stdout}\n{result.stderr}"
    return json.loads(lines[-1])


# ── Answer check ─────────────────────────────────────────────────────────────

_ANSWER_FAKES = r"""
$script:Written = $null
$script:ModelCalls = 0
function script:Get-IssueState {
    param([int]$IssueNumber)
    [pscustomobject]@{
        readiness          = [pscustomobject]@{ refined = [pscustomobject]@{ done = $true } }
        questions_asked_at = '2026-09-23T10:00:00Z'
        open_questions     = @(
            [pscustomobject]@{ text = 'Allowlist or denylist?'; raised_by = 'grill'; decision = 'allowlist' },
            [pscustomobject]@{ text = 'Where does it live?';    raised_by = 'grill'; decision = 'Config.ps1' }
        )
        decided_questions  = @([pscustomobject]@{ text = 'earlier'; decision = 'kept' })
    }
}
function script:Set-PlanningState { param([int]$IssueNumber, $State) $script:Written = $State }
function script:gh { $global:LASTEXITCODE = 0; '{"title":"t","body":"b"}' }
"""


def test_answer_check_records_answers_and_follow_ups() -> None:
    out = _run(
        _ANSWER_FAKES
        + r"""
function script:Get-OwnerComments { param($IssueNumber, $Since)
    @([pscustomobject]@{ login = 'octocat'; created_at = '2026-09-23T11:00:00Z'; body = '1 allowlist. 2 not sure yet' }) }
function script:claude { $script:ModelCalls++; $global:LASTEXITCODE = 0
    '{"answers":[{"id":1,"status":"answered","decision":"Use an allowlist."},{"id":2,"status":"open","follow_up":"Config.ps1 or settings.json?"}],"new_questions":[{"text":"Include docs/?","recommendation":"yes"}]}' }
$r = Invoke-AnswerCheck -IssueNumber 50
[pscustomobject]@{
    evaluated = $r.Evaluated; answered = $r.Answered; open = $r.Open; calls = $script:ModelCalls
    decided   = @($script:Written.decided_questions | ForEach-Object { "$($_.text)|$($_.decision)|$($_.decided_by)" })
    still     = @($script:Written.open_questions | ForEach-Object { "$($_.text)|$($_.follow_up)" })
    asked     = [string]$script:Written.questions_asked_at
} | ConvertTo-Json -Compress
"""
    )
    assert out["evaluated"] is True
    assert (out["answered"], out["open"], out["calls"]) == (1, 2, 1)
    assert out["decided"] == [
        "earlier|kept|",
        "Allowlist or denylist?|Use an allowlist.|octocat",
    ]
    assert out["still"] == [
        "Where does it live?|Config.ps1 or settings.json?",
        "Include docs/?|",
    ]
    assert out["asked"] and out["asked"] != "2026-09-23T10:00:00Z"


def test_answer_check_without_a_new_reply_calls_no_model() -> None:
    out = _run(
        _ANSWER_FAKES
        + r"""
function script:Get-OwnerComments { param($IssueNumber, $Since) @() }
function script:claude { throw 'the model must not be called without a new owner reply' }
$r = Invoke-AnswerCheck -IssueNumber 50
[pscustomobject]@{ evaluated = $r.Evaluated; open = $r.Open; written = ($null -ne $script:Written) } |
    ConvertTo-Json -Compress
"""
    )
    assert out == {"evaluated": False, "open": 2, "written": False}


def test_answer_check_reports_an_unusable_model_reply() -> None:
    out = _run(
        _ANSWER_FAKES
        + r"""
function script:Get-OwnerComments { param($IssueNumber, $Since)
    @([pscustomobject]@{ login = 'octocat'; created_at = 'x'; body = 'ok' }) }
function script:claude { $global:LASTEXITCODE = 0; 'I think so?' }
$r = Invoke-AnswerCheck -IssueNumber 50
[pscustomobject]@{ error = [bool]$r.Error; written = ($null -ne $script:Written) } | ConvertTo-Json -Compress
"""
    )
    assert out == {"error": True, "written": False}


def test_answer_check_reports_a_failed_comment_read() -> None:
    """A failed read must surface as an error, never pass as 'no reply' (#158)."""
    out = _run(
        _ANSWER_FAKES
        + r"""
function script:gh { $global:LASTEXITCODE = 1; 'HTTP 422' }
function script:claude { throw 'the model must not be called when comments could not be read' }
$r = Invoke-AnswerCheck -IssueNumber 50
[pscustomobject]@{ error = "$($r.Error)"; written = ($null -ne $script:Written) } | ConvertTo-Json -Compress
"""
    )
    assert "HTTP 422" in out["error"]
    assert out["written"] is False


# ── Comments ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "since",
    [
        # The carrier round-trip: ConvertFrom-Json yields a [datetime] (#158).
        '(\'{"at":"2026-09-23T23:05:54.0910580Z"}\' | ConvertFrom-Json).at',
        "'2026-09-23T23:05:54.0910580Z'",
        "'2026-09-24T01:05:54+02:00'",
    ],
)
def test_owner_comments_send_since_in_the_api_format(since: str) -> None:
    out = _run(
        rf"""
function script:gh {{ $script:Path = $args[2]; $global:LASTEXITCODE = 0 }}
$null = Get-OwnerComments -IssueNumber 7 -Since ({since})
[pscustomobject]@{{ path = $script:Path }} | ConvertTo-Json -Compress
"""
    )
    assert out["path"].endswith("&since=2026-09-23T23:05:54Z"), out["path"]


def test_add_comment_always_carries_a_pipeline_prefix() -> None:
    """afk.yml ignores 🤖/· comments; an unprefixed pipeline comment would re-trigger it."""
    out = _run(
        r"""
$script:Posted = @()
function script:gh { $f = $args[$args.IndexOf('--body-file') + 1]; $script:Posted += (Get-Content $f -Raw).Trim(); $global:LASTEXITCODE = 0 }
Add-Comment -Number 1 -Body 'plain text'
Add-Comment -Number 1 -Body '🤖✅ signal'
Add-Comment -Number 1 -Body '· noise'
[pscustomobject]@{ posted = $script:Posted } | ConvertTo-Json -Compress
"""
    )
    assert out["posted"] == ["· plain text", "🤖✅ signal", "· noise"]


def test_owner_comments_filter_trusted_humans_only() -> None:
    """The filter runs as gh's jq, so assert its terms; then that each line parses."""
    source = (REPO_ROOT / ".github/orchestrator/lib/GitHub.ps1").read_text(
        encoding="utf-8"
    )
    block = source[source.index("function Get-OwnerComments") :]
    block = block[: block.index("\n}\n")]
    for term in (
        '"OWNER"',
        '"MEMBER"',
        '"COLLABORATOR"',
        'startswith("🤖")',
        "--paginate",
    ):
        assert term in block, term
    out = _run(
        r"""
function script:gh { $global:LASTEXITCODE = 0
    '{"login":"a","created_at":"t1","body":"first\nline"}'
    '{"login":"b","created_at":"t2","body":"second"}' }
$c = @(Get-OwnerComments -IssueNumber 7 -Since '2026-01-01T00:00:00Z')
[pscustomobject]@{ n = $c.Count; last = $c[-1].body; first = $c[0].body } | ConvertTo-Json -Compress
"""
    )
    assert out == {"n": 2, "last": "second", "first": "first\nline"}


# ── Body sections ────────────────────────────────────────────────────────────


def test_decision_section_lists_options_and_decided() -> None:
    out = _run(
        r"""
function script:Set-IssueBodySection { param($IssueNumber, $BeginMarker, $EndMarker, $Markdown) $script:Md = $Markdown; $true }
$state = [pscustomobject]@{
    open_questions    = @([pscustomobject]@{ text = 'Q1?'; decision = 'rec'; alternatives = @('alt b', 'alt c'); follow_up = 'which one?' })
    decided_questions = @([pscustomobject]@{ text = 'Q0?'; decision = 'yes'; decided_by = 'octocat' })
}
Set-DecisionSection -IssueNumber 1 -State $state
[pscustomobject]@{ md = $script:Md } | ConvertTo-Json -Compress
"""
    )
    md = out["md"]
    assert md.startswith("## Decisions")
    for line in (
        "**1. Q1?**",
        "- **A — recommended:** rec",
        "- **B:** alt b",
        "- **C:** alt c",
        "- **Other:** your own answer",
        "- _Still needed:_ which one?",
        "- Q0? → yes _(octocat)_",
    ):
        assert line in md, line
    assert "`ok` — accept every recommendation" in md


def test_request_decisions_asks_in_the_issue_with_a_reply_guide() -> None:
    out = _run(
        r"""
$script:State = [pscustomobject]@{
    open_questions = @(
        [pscustomobject]@{ text = 'First?';  decision = 'yes'; alternatives = @('no', 'later') },
        [pscustomobject]@{ text = 'Second?'; decision = 'X';   alternatives = @('Y', 'Z') }
    )
}
function script:Get-IssueState { param($IssueNumber) $script:State }
function script:Set-PlanningState { param($IssueNumber, $State) $script:State = $State }
function script:Set-DecisionSection { param($IssueNumber, $State) }
function script:Set-AgentState { param($IssueNumber, $Label) $script:Label = $Label }
function script:Set-IssueLabel { throw 'labels go through Set-AgentState (#225)' }
function script:Add-Comment { param($Number, $Body) $script:Body = $Body }
Request-Decisions -IssueNumber 50
[pscustomobject]@{ body = $script:Body; label = $script:Label; asked = [bool]$script:State.questions_asked_at } |
    ConvertTo-Json -Compress
"""
    )
    body = out["body"]
    assert body.startswith("🤖⏸ Needs your decision — 2 question(s)")
    assert "**2. Second?**" in body and "- **C:** Z" in body
    assert "`ok` — accept every recommendation" in body and "`1B`" in body
    assert out["label"] == "human:decision" and out["asked"] is True


def test_failed_attempts_are_recorded_in_the_issue() -> None:
    out = _run(
        r"""
$script:State = [pscustomobject]@{ open_questions = @() }
function script:Get-IssueState { param($IssueNumber) $script:State }
function script:Set-PlanningState { param($IssueNumber, $State) $script:State = $State }
function script:Set-IssueBodySection { param($IssueNumber, $BeginMarker, $EndMarker, $Markdown) $script:Md = $Markdown; $true }
Add-FailedAttempt -IssueNumber 1 -Stage 'implement' -Reason "tests failed`nline two" -Attempt 1 -Max 3
Add-FailedAttempt -IssueNumber 1 -Stage 'ship' -Reason 'CI checks failed for PR #9: test' -Attempt 2 -Max 3
$mid = $script:Md
Add-FailedAttempt -IssueNumber 1 -Stage 'review' -Reason 'rejected' -Attempt 3 -Max 3
$final = $script:Md
Reset-AttemptCount -IssueNumber 1
[pscustomobject]@{
    mid = $mid; final = $final; reset = $script:Md
    count = $script:State.attempt_count; history = @($script:State.attempts).Count
} | ConvertTo-Json -Compress
"""
    )
    assert "retrying — 2/3 attempts used" in out["mid"]
    assert "**Attempt 1/3** · implement" in out["mid"]
    assert "tests failed line two" in out["mid"]
    assert "failed 3/3 — waiting on you" in out["final"]
    # A new round keeps the history and clears the count.
    assert (out["count"], out["history"]) == (0, 3)
    assert "no failure in the current round" in out["reset"]


# ── Board ────────────────────────────────────────────────────────────────────


def test_issue_missing_from_the_board_is_added_and_cached() -> None:
    out = _run(
        r"""
$script:KanbanProjectNumber = 5
$script:_CachedItems = @([pscustomobject]@{
    id = 'PVTI_other'; content = [pscustomobject]@{ number = 1; repository = 'octocat/sandbox' }
})
$script:KanbanOpt_Backlog = 'opt_backlog'
$script:_CachedProjectId = 'PVT_1'
function script:Get-ResolvedOwner { 'octocat' }
$script:Calls = @()
function script:gh { $script:Calls += ($args -join ' '); $global:LASTEXITCODE = 0; '{"id":"PVTI_new"}' }
$added = Add-IssueToBoard -IssueNumber 42
$again = Add-IssueToBoard -IssueNumber 42
[pscustomobject]@{
    added = $added; again = $again; itemId = (Get-ProjectItemId -IssueNumber 42)
    calls = @($script:Calls); status = (Get-ProjectStatus -IssueNumber 42)
} | ConvertTo-Json -Compress
"""
    )
    assert out["added"] is True and out["again"] is True
    assert out["itemId"] == "PVTI_new"
    # Added once, then placed in Backlog once: an item without a Status can be
    # hidden by a board view.
    add, edit = out["calls"]
    assert add.startswith("project item-add") and "issues/42" in add
    assert edit.startswith("project item-edit") and "opt_backlog" in edit
    assert out["status"] == "Backlog"


def test_board_unreadable_means_no_add() -> None:
    out = _run(
        r"""
$script:KanbanProjectNumber = 5
$script:_CachedItems = $null
$script:_ItemsFailed = $true
function script:gh { throw 'gh must not be called when the board could not be read' }
[pscustomobject]@{ added = (Add-IssueToBoard -IssueNumber 42) } | ConvertTo-Json -Compress
"""
    )
    assert out == {"added": False}


# ── Refine: no Agent Brief, no readiness ────────────────────────────────────


def test_failed_grill_fails_refine_and_never_marks_it_refined() -> None:
    """Live on #212 the grill failed and refine still set readiness.refined, so the
    issue earned agent:backlog without anyone checking what the owner must decide."""
    out = _run(
        r"""
$script:Log = [System.Collections.Generic.List[string]]::new()
function script:gh { $global:LASTEXITCODE = 0; '{"title":"t","body":"**Goal**: g","comments":[]}' }
function script:Get-IssueTemplate { '**Goal**: <goal>' }
function script:Get-ProjectFieldValues { param($IssueNumber) [pscustomobject]@{ estimate = 3; priority = 'P2' } }
function script:Format-OwnerComments { param($IssueNumber) '' }
function script:Invoke-Grill { param($Title, $Body) throw "Self-grill subagent stopped with 'error_max_turns'" }
function script:Set-PlanningReadiness { param($IssueNumber, $Stage, $StageLabel, $PopulatedBy) $script:Log.Add("ready:$Stage") }
function script:Add-Comment { param($Number, $Body) $script:Log.Add('comment') }
$err = $null
try { Invoke-Refine -Number 7 } catch { $err = $_.Exception.Message }
[pscustomobject]@{ err = $err; log = @($script:Log) } | ConvertTo-Json -Compress
"""
    )
    assert "error_max_turns" in out["err"]
    assert out["log"] == []


# ── Conductor ────────────────────────────────────────────────────────────────

_CONDUCTOR_FAKES = r"""
$script:Log = [System.Collections.Generic.List[string]]::new()
function script:Assert-EngineReady {}
function script:Test-TrustedAuthor { param($IssueNumber) $true }
function script:Acquire-OrchestratorLock { param($IssueNumber) $true }
function script:Release-OrchestratorLock {}
function script:Add-IssueToBoard { param($IssueNumber) $true }
function script:Add-Comment { param($Number, $Body) $script:Log.Add("comment:" + ($Body -split "`n")[0]) }
function script:Set-AgentState { param($IssueNumber, $Label) $script:Log.Add("state:$Label") }
function script:Set-IssueLabel { param($Number, $Add, $Remove) $script:Log.Add("label:+$Add-$Remove") }
function script:Set-AgentFailedState { param($IssueNumber, $FailedAt, $Reason) $script:Log.Add("failed:$FailedAt") }
function script:Set-DecisionSection { param($IssueNumber, $State) }
function script:Format-ErrorBlock { param($Raw) $Raw }
function script:git { $global:LASTEXITCODE = 1 }
# Never call a real model from a test: the usage-limit probe answers "not limited".
function script:Test-EngineUsageLimit { $null }
"""


def _conductor(body: str, tmp_path: Path) -> dict:
    return _run(_CONDUCTOR_FAKES + body, cwd=tmp_path)


_WAITING_STATE = r"""
$script:Ready = $false
function script:Get-IssueState { param($IssueNumber)
    [pscustomobject]@{
        readiness      = [pscustomobject]@{ refined = [pscustomobject]@{ done = $true } }
        open_questions = $(if ($script:Ready) { @() } else { @([pscustomobject]@{ text = 'q' }) })
    } }
function script:Test-Readiness { param($State) $script:Ready }
function script:gh { $global:LASTEXITCODE = 0; '{"title":"t","labels":[{"name":"human:decision"}],"state":"OPEN"}' }
"""


def test_waiting_issue_without_a_reply_does_nothing(tmp_path: Path) -> None:
    out = _conductor(
        _WAITING_STATE
        + r"""
function script:Invoke-AnswerCheck { param($IssueNumber) [pscustomobject]@{ Evaluated = $false; Answered = 0; Open = 1; Error = $null } }
function script:Invoke-Refine { throw 'no re-refine without a reply' }
$r = Invoke-Orchestration -From refine -IssueNumber 50
[pscustomobject]@{ result = $r; log = @($script:Log) } | ConvertTo-Json -Compress
""",
        tmp_path,
    )
    assert out == {"result": False, "log": []}


def test_all_answered_re_plans_and_grants_backlog(tmp_path: Path) -> None:
    out = _conductor(
        _WAITING_STATE
        + r"""
function script:Invoke-AnswerCheck { param($IssueNumber) $script:Ready = $true
    [pscustomobject]@{ Evaluated = $true; Answered = 1; Open = 0; Error = $null } }
function script:Invoke-Refine    { param($Number)      $script:Log.Add('refine') }
function script:Invoke-Architect { param($IssueNumber) $script:Log.Add('architect') }
function script:Invoke-Plan      { param($Number)      $script:Log.Add('plan') }
function script:Reset-AttemptCount { param($IssueNumber) }
$r = Invoke-Orchestration -From refine -IssueNumber 50
[pscustomobject]@{ result = $r; log = @($script:Log) } | ConvertTo-Json -Compress
""",
        tmp_path,
    )
    assert out["result"] is True
    # agent:refining is set once work is confirmed, then stages run, then agent:backlog.
    assert out["log"][:4] == ["state:agent:refining", "refine", "architect", "plan"]
    # agent:backlog replaces agent:refining in one Set-AgentState call (#225).
    assert not any(e.startswith("label:") for e in out["log"])
    assert "state:agent:backlog" in out["log"]


def test_held_issue_never_re_enters_refine(tmp_path: Path) -> None:
    """A comment on a PR held for the owner's merge must not re-plan the issue (#225)."""
    out = _conductor(
        r"""
function script:Get-IssueState { param($IssueNumber)
    [pscustomobject]@{ readiness = [pscustomobject]@{ planned = [pscustomobject]@{ done = $true } }; open_questions = @() } }
function script:gh { $global:LASTEXITCODE = 0; '{"title":"t","labels":[{"name":"human:approval"}],"state":"OPEN"}' }
function script:Invoke-Refine { throw 'a held issue must not be refined again' }
$r = Invoke-Orchestration -From refine -IssueNumber 50
[pscustomobject]@{ result = $r; log = @($script:Log) } | ConvertTo-Json -Compress
""",
        tmp_path,
    )
    assert out == {"result": False, "log": []}


def test_partial_answer_asks_again(tmp_path: Path) -> None:
    out = _conductor(
        _WAITING_STATE
        + r"""
function script:Invoke-AnswerCheck { param($IssueNumber) [pscustomobject]@{ Evaluated = $true; Answered = 1; Open = 1; Error = $null } }
function script:Request-Decisions { param($IssueNumber, $Answered) $script:Log.Add("ask:$Answered") }
function script:Invoke-Refine { throw 'no re-refine while a question is open' }
$r = Invoke-Orchestration -From refine -IssueNumber 50
[pscustomobject]@{ result = $r; log = @($script:Log) } | ConvertTo-Json -Compress
""",
        tmp_path,
    )
    assert out == {"result": False, "log": ["ask:1"]}


_IMPLEMENT_FAKES = r"""
$script:State = [pscustomobject]@{ attempts = @(); attempt_count = 0 }
function script:Get-IssueState { param($IssueNumber) $script:State }
function script:Add-FailedAttempt { param($IssueNumber, $Stage, $Reason, $Attempt, $Max) $script:Log.Add("attempt:$Attempt/$Max@$Stage") }
function script:Reset-AttemptCount { param($IssueNumber) $script:Log.Add('reset') }
function script:gh { $global:LASTEXITCODE = 0
    if ($args[0] -eq 'pr') { '[{"number":9}]' } else { '{"title":"t","labels":[],"state":"OPEN"}' } }
function script:Invoke-Review { param($IssueNumber, $PRNumber) $true }
function script:Invoke-Ship   { param($IssueNumber, $PRNumber) $script:Log.Add('ship'); $true }
$script:Calls = 0
"""


def test_attempt_loop_recovers_on_the_second_attempt(tmp_path: Path) -> None:
    out = _conductor(
        _IMPLEMENT_FAKES
        + r"""
function script:Invoke-Implement { param($IssueNumber, [switch]$Force)
    $script:Calls++; $script:Log.Add("implement:force=$([bool]$Force)")
    if ($script:Calls -eq 1) { throw 'Test suite failed after implementation for issue #50' }
    'https://github.com/octocat/sandbox/pull/9' }
Invoke-Orchestration -IssueNumber 50 -MaxRetries 3
[pscustomobject]@{ log = @($script:Log) } | ConvertTo-Json -Compress
""",
        tmp_path,
    )
    log = out["log"]
    assert "implement:force=False" in log and "implement:force=True" in log
    assert "attempt:1/3@implement" in log
    assert log[-2:] == ["ship", "reset"]
    assert not any(e.startswith("failed:") for e in log)


def test_attempt_loop_fails_only_after_the_budget(tmp_path: Path) -> None:
    out = _conductor(
        _IMPLEMENT_FAKES
        + r"""
function script:Invoke-Implement { param($IssueNumber, [switch]$Force) 'https://github.com/octocat/sandbox/pull/9' }
function script:Invoke-Review { param($IssueNumber, $PRNumber) $script:Calls++; $false }
Invoke-Orchestration -IssueNumber 50 -MaxRetries 3
[pscustomobject]@{ log = @($script:Log); reviews = $script:Calls } | ConvertTo-Json -Compress
""",
        tmp_path,
    )
    log = out["log"]
    assert out["reviews"] == 3
    assert [e for e in log if e.startswith("attempt:")] == [
        "attempt:1/3@review",
        "attempt:2/3@review",
        "attempt:3/3@review",
    ]
    assert "failed:review" in log and "ship" not in log
    assert any(e.startswith("comment:🤖❌ Failed after 3 attempts") for e in log)


def test_refine_failures_use_the_attempt_budget_then_fail(tmp_path: Path) -> None:
    out = _conductor(
        _IMPLEMENT_FAKES
        + r"""
function script:Get-IssueState { param($IssueNumber) $null }
function script:Invoke-Refine { param($Number) $script:Calls++; throw 'Self-grill subagent gave no result' }
function script:Test-Readiness { param($State) $true }
$r = Invoke-Orchestration -From refine -IssueNumber 50 -MaxRetries 3
[pscustomobject]@{ r = $r; log = @($script:Log); calls = $script:Calls } | ConvertTo-Json -Compress
""",
        tmp_path,
    )
    assert out["r"] is False and out["calls"] == 3
    assert "failed:refine" in out["log"]
    assert "state:agent:backlog" not in out["log"]
