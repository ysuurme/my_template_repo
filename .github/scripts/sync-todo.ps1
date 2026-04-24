# .github/scripts/sync-todo.ps1
# Synchronizes TODO.md ISSUE blocks with GitHub Projects/Issues.

param(
    [switch]$DryRun
)

$TodoPath = "TODO.md"
if (-not (Test-Path $TodoPath)) {
    Write-Error "TODO.md not found in the root directory."
    exit 1
}

$Content = Get-Content $TodoPath -Raw
# Regex to match ISSUE blocks accurately including nested content
$IssueRegex = "(?s)ISSUE:\s*(.*?)\r?\n(.*?)\r?\nEND_ISSUE"
$Matches = [regex]::Matches($Content, $IssueRegex)

if ($Matches.Count -eq 0) {
    Write-Host "✅ No pending ISSUE blocks found in TODO.md." -ForegroundColor Green
    exit 0
}

Write-Host "🚀 Found $($Matches.Count) issue(s) to synchronize." -ForegroundColor Cyan

$ProcessedIssues = @()
$NewContent = $Content

foreach ($Match in $Matches) {
    $FullBlock = $Match.Value
    $Title = $Match.Groups[1].Value.Trim()
    $Body = $Match.Groups[2].Value.Trim()

    Write-Host "Processing: '$Title'..." -ForegroundColor Yellow

    if ($DryRun) {
        Write-Host "[DRY RUN] Would create issue: $Title" -ForegroundColor Gray
        continue
    }

    # Attempt to create GitHub issue
    Write-Host "Creating issue..." -ForegroundColor Yellow
    
    # Use a temporary file for the body to avoid shell escaping issues
    $TempFile = [System.IO.Path]::GetTempFileName()
    $Body | Out-File $TempFile -Encoding utf8
    
    $Result = gh issue create --title $Title --body-file $TempFile 2>&1
    Remove-Item $TempFile
    
    if ($LASTEXITCODE -eq 0) {
        $IssueUrl = ($Result | Out-String).Trim()
        Write-Host "✅ Created: $IssueUrl" -ForegroundColor Green
        # Queue for removal from file
        $ProcessedIssues += $FullBlock
    } else {
        Write-Host "❌ Failed to create issue '$Title'." -ForegroundColor Red
        Write-Host "Error details: $Result" -ForegroundColor Gray
    }
}

if (-not $DryRun -and $ProcessedIssues.Count -gt 0) {
    Write-Host "♻️  Burning down $($ProcessedIssues.Count) issue(s) from TODO.md..." -ForegroundColor Yellow
    foreach ($Block in $ProcessedIssues) {
        # Escape for regex and ensure we handle whitespace/newlines correctly during replacement
        $EscapedBlock = [regex]::Escape($Block)
        # Add optional trailing newline to clean up the file
        $NewContent = [regex]::Replace($NewContent, "$EscapedBlock\s*", "")
    }
    
    # Clean up excess empty lines
    $NewContent = $NewContent -replace "(\r?\n){3,}", "`r`n`r`n"
    $NewContent.Trim() | Out-File $TodoPath -Encoding utf8
    Write-Host "🎉 TODO.md updated." -ForegroundColor Cyan
}

if ($DryRun) {
    Write-Host "✨ Dry run complete. No changes made." -ForegroundColor Cyan
}
