<#
Safely fast-forward Zenvibe without deleting any local database or generated
preview files. This resolves "untracked working tree files would be overwritten"
by moving ONLY colliding local untracked files to a timestamped folder OUTSIDE
the repository before pulling. Never uses git clean/reset/force.

Usage from the repository root:
    powershell -ExecutionPolicy Bypass -File scripts\safe_pull_templates.ps1

The saved originals (particularly calendar photos) remain in the backup folder.
Git may install tracked files at their previous paths. If you need the original
bytes for your local database, compare against the backup before using them.
#>
[CmdletBinding()]
param(
    [string]$Branch = "feature/calendar-editable-templates"
)
$ErrorActionPreference = "Stop"
$root = (& git rev-parse --show-toplevel 2>$null)
if ($LASTEXITCODE -ne 0 -or -not $root) {
    throw "Run this script from inside the Zenvibe Git repository."
}
$root = $root.Trim()
Push-Location -LiteralPath $root
try {
    $branchName = (& git branch --show-current).Trim()
    if ($branchName -ne $Branch) {
        throw "Current branch is '$branchName', expected '$Branch'. Checkout the correct branch first."
    }

    $dirtyTracked = @(& git diff --name-only) + @(& git diff --cached --name-only)
    $dirtyTracked = @($dirtyTracked | Where-Object { $_ -and $_.Trim() })
    if ($dirtyTracked.Count) {
        throw (
            "Tracked local edits found ($($dirtyTracked.Count)). Commit or stash tracked edits " +
            "before pulling; no files were moved."
        )
    }

    & git fetch origin $Branch
    if ($LASTEXITCODE -ne 0) { throw "Git fetch failed; no local files were moved." }

    $target = "origin/$Branch"
    $remoteFiles = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)
    @(& git ls-tree -r --name-only $target) | ForEach-Object {
        if ($_ -and $_.Trim()) { [void]$remoteFiles.Add($_.Trim()) }
    }
    if ($LASTEXITCODE -ne 0 -or $remoteFiles.Count -eq 0) {
        throw "Could not read the target branch file tree."
    }

    $untracked = @(& git ls-files --others --exclude-standard --full-name)
    if ($LASTEXITCODE -ne 0) { throw "Could not list untracked local files." }
    $collisions = @(
        $untracked | Where-Object { $_ -and $remoteFiles.Contains($_.Trim()) }
    )

    $backup = $null
    $moved = @()
    if ($collisions.Count) {
        $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
        $backup = Join-Path (Split-Path -Parent $root) ("zenvibe_pull_conflicts_$stamp")
        New-Item -ItemType Directory -Path $backup -Force | Out-Null
        Write-Host "Saving $($collisions.Count) colliding files outside the repository: $backup"

        foreach ($gitPath in $collisions) {
            $relative = $gitPath.Trim().Replace("/", [IO.Path]::DirectorySeparatorChar)
            $source = Join-Path $root $relative
            $destination = Join-Path $backup $relative
            $destinationFolder = Split-Path -Parent $destination
            New-Item -ItemType Directory -Path $destinationFolder -Force | Out-Null
            # Move (not copy+delete) is fast and keeps original file contents.
            Move-Item -LiteralPath $source -Destination $destination -ErrorAction Stop
            $moved += $gitPath
        }
        $moved | Set-Content -LiteralPath (Join-Path $backup "moved_file_paths.txt")
    }

    & git pull --ff-only origin $Branch
    if ($LASTEXITCODE -ne 0) {
        throw (
            "Fast-forward pull failed. Your colliding files remain safely backed up " +
            "at '$backup'; the database was not touched."
        )
    }

    Write-Host "Safe pull completed: $((& git rev-parse --short HEAD).Trim())"
    if ($backup) {
        # Calendars are APPROVED artwork. If GitHub contains a different
        # calendar preview under the same filename, retain the original local
        # image referenced by this installation's database. Do not modify
        # calendars' generator, template JSON or product settings.
        $restoredCalendar = 0
        foreach ($gitPath in $collisions) {
            if ($gitPath -notmatch '^media/template_previews/calendar_') {
                continue
            }
            $relative = $gitPath.Trim().Replace("/", [IO.Path]::DirectorySeparatorChar)
            $source = Join-Path $backup $relative
            $local = Join-Path $root $relative
            if ((Test-Path -LiteralPath $source) -and (Test-Path -LiteralPath $local)) {
                $oldHash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
                $newHash = (Get-FileHash -LiteralPath $local -Algorithm SHA256).Hash
                if ($oldHash -ne $newHash) {
                    Copy-Item -LiteralPath $source -Destination $local -Force
                    $restoredCalendar += 1
                }
            }
        }
        Write-Host "Backed-up local originals: $backup"
        if ($restoredCalendar) {
            Write-Warning (
                "$restoredCalendar local calendar images differed from GitHub and were " +
                "restored to keep your approved calendar unchanged. Git may list these " +
                "calendar images as modified: review before a later pull."
            )
        }
    }
    Write-Host "Django database, reports, backups and unrelated local files were not deleted."
}
finally {
    Pop-Location
}
