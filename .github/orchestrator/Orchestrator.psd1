@{
    RootModule        = 'Orchestrator.psm1'
    ModuleVersion     = '2.0.0'
    GUID              = '7b976e4f-53df-487d-ab4c-1bd36d42699e'
    Author            = 'agentic-sdlc'
    Description       = 'Agentic pipeline orchestrator: refine -> architect -> plan -> implement -> review -> ship. Run parameters flow via the KANBAN_* env transport and Get-OrchestratorContext (ADR-013, ADR-015).'
    PowerShellVersion = '7.0'

    # The public API. This is the ONLY place it is declared — a manifest is data,
    # whereas Export-ModuleMember would be logic running at import (ADR-015).
    #
    # Listed explicitly, never '*': with an explicit list PowerShell resolves which
    # module provides a command from this file alone, without loading or executing
    # the module. A wildcard forces a full load to answer the same question, and
    # exported all 78 functions the module defines when only these are called from
    # outside it.
    #
    # Anything absent here is private to the module automatically. No underscore
    # convention and no internal/ directory are needed — this list is the boundary.
    # checks/check-orchestrator-api.ps1 asserts it stays true.
    FunctionsToExport = @(
        # Run context
        'Get-OrchestratorContext'

        # The conductor
        'Invoke-Orchestration'

        # Stages invoked directly (by tasks/ and the workflows)
        'Invoke-Ship'

        # Issue + board state
        'Move-ToLane'
        'Resolve-PR'

        # Hourly resume of issues paused on the engine's usage limit (afk.yml)
        'Resume-PausedIssues'

        # Recovery (lib/Reconcile.ps1). Invoke-Reconciliation is the hourly warden
        # over states nothing is working on; Restart-Issue is the single re-entry
        # point it and task retry both use.
        #
        # Collapsing task retry onto Restart-Issue took five functions out of this
        # list — Set-AgentState, Add-Comment, Reset-AttemptCount, Get-IssueState and
        # Set-IssueLabel. retry.ps1 was their only external caller, and it had to
        # sequence all five by hand to do what Restart-Issue now does in one call.
        # That sequence was a second copy of the re-entry rule, and it had drifted:
        # it keyed on failed_at, which a killed runner never records. A narrower
        # surface is the point of ADR-015 — Set-AgentState in particular should not
        # be reachable from outside the module that owns every transition.
        'Invoke-Reconciliation'
        'Restart-Issue'

        # The owner merged or closed a PR held for approval (afk.yml)
        'Complete-HeldPR'

        # The single "is this issue already shipped" rule — afk.yml's pr-closed
        # cheap pre-check and Complete-HeldPR's own guard both call this (#275)
        'Test-IssueShipped'

        # Self-grill subagent (refine stage; also driven standalone by the
        # refine skill's grill.ps1 probe)
        'Invoke-Grill'

        # Shared helpers used by the task scripts
        'Write-Log'
        'Set-EnvVar'
        'Get-ResolvedOwner'
    )

    # Never variables: the $Kanban* run state stays private so it cannot leak into
    # a caller's scope — the scope leak that once ran the pipeline against issue #0
    # (ADR-013).
    CmdletsToExport   = @()
    VariablesToExport = @()
    AliasesToExport   = @()
}
