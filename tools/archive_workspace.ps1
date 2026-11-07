param([switch]$Apply)
$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$workspaceRoot = [IO.Path]::GetFullPath((Split-Path -Parent $repoRoot))
$workspaceArchive = Join-Path $workspaceRoot 'archive\2026-11-07'
$repoArchive = Join-Path $repoRoot 'archive\2026-11-07'
$manifestPath = Join-Path $workspaceArchive 'manifest.json'
$journal = [Collections.Generic.List[object]]::new()
$plans = [Collections.Generic.List[object]]::new()

function Add-Plan([string]$From, [string]$To, [string]$Reason) {
    $plans.Add([pscustomobject]@{ Source = $From; Destination = $To; Reason = $Reason })
}

foreach ($name in @('pitch-deck.html','pitch-deck-v4.html','pitch-deck-template-v3.html','pitch-deck-parkflow-v2.html','pitch-deck-parkahead-v1.html','pitch-deck.pptx','~$pitch-deck.pptx','business-proposal.html','week1-progress.html','simedarby_logo.png','ParkFlow.zip','deck','analysis','.codex-preview')) {
    Add-Plan (Join-Path $workspaceRoot $name) (Join-Path $workspaceArchive "workspace\$name") 'Superseded workspace draft, toolchain, duplicate analysis or historical preview'
}
foreach ($name in @('briefing-transcript-2026-10-09.md','business_context.md','data_high_value.md','proposal.md')) {
    Add-Plan (Join-Path $workspaceRoot $name) (Join-Path $workspaceRoot "source-material\$name") 'Retained active briefing/reference material, grouped for clarity'
}
foreach ($name in @('ParkFlow-Priority-Zone-Business-Case-vNext.pdf','ParkFlow-Priority-Zone-Business-Case-vNext.pptx','ParkFlow-Team-Hexa-Pitch-Deck-final.pdf','ParkFlow-Team-Hexa-Pitch-Deck-v2.html','ParkFlow-Team-Hexa-Pitch-Deck-v3.html','ParkFlow-Team-Hexa-Pitch-Deck.html','pitch-deck.pptx')) {
    Add-Plan (Join-Path $repoRoot "submission\$name") (Join-Path $repoArchive "submission\$name") 'Superseded presentation export; current consulting/original-deck PDFs remain active'
}
foreach ($name in @('build_deck.py','generated','render','ParkFlow-Priority-Zone-Business-Case-vNext.pdf')) {
    Add-Plan (Join-Path $repoRoot "presentation\$name") (Join-Path $repoArchive "presentation\$name") 'Legacy PowerPoint generator or generated rendering; no current HTML pipeline dependency'
}
Add-Plan (Join-Path $repoRoot 'references\parkflow-site-v2') (Join-Path $repoArchive 'references\parkflow-site-v2') 'Snapshot consumed only by the archived PowerPoint generator'

# Resolve and validate every move before mutating any filesystem entry.
foreach ($entry in $plans) {
    $entry.Source = [IO.Path]::GetFullPath($entry.Source)
    $entry.Destination = [IO.Path]::GetFullPath($entry.Destination)
    if (!$entry.Source.StartsWith($workspaceRoot + '\', [StringComparison]::OrdinalIgnoreCase) -or
        !$entry.Destination.StartsWith($workspaceRoot + '\', [StringComparison]::OrdinalIgnoreCase) -or
        $entry.Source -eq $workspaceRoot -or $entry.Source -eq $repoRoot -or
        $entry.Source -match '\\\.git(?:\\|$)' -or $entry.Source -match '\\\.env$' -or
        $entry.Destination.StartsWith($entry.Source + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw "Unsafe target rejected: $($entry.Source) -> $($entry.Destination)"
    }
    if ((Test-Path -LiteralPath $entry.Source) -and (Test-Path -LiteralPath $entry.Destination)) {
        throw "Destination already exists; no overwrite allowed: $($entry.Destination)"
    }
}
if (!$Apply) {
    $plans | Select-Object Source, Destination, Reason | ConvertTo-Json -Depth 4
    exit 0
}
if (Test-Path -LiteralPath $manifestPath) { throw 'An archive journal already exists; inspect it before another run.' }

$protected = @('site-consulting\index.html','site-consulting\deck.css','site-consulting\premium.css','site-consulting\deck.js','site-vnext\index.html','docs\index.html','docs\command.html','docs\driver.html','package.json','submission\ParkFlow-Consulting-Deck.pdf','submission\ParkFlow-Main-Deck.pdf','submission\ParkFlow-Appendix.pdf','submission\ParkFlow-Deck-With-Appendix.pdf')
$protectedBefore = @{}
foreach ($relative in $protected) {
    $path = Join-Path $repoRoot $relative
    $protectedBefore[$relative] = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
}
[IO.Directory]::CreateDirectory($workspaceArchive) | Out-Null
foreach ($entry in $plans) {
    if (!(Test-Path -LiteralPath $entry.Source)) { continue }
    $item = Get-Item -LiteralPath $entry.Source -Force
    $record = [pscustomobject]@{ Source=$entry.Source; Destination=$entry.Destination; Reason=$entry.Reason; Status='planned'; Error=$null; Files=@() }
    $journal.Add($record)
    try {
        if (!$item.PSIsContainer -and $item.Extension -eq '.pptx') {
            $handle = [IO.File]::Open($item.FullName, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::None)
            $handle.Dispose()
        }
        $files = if ($item.PSIsContainer) { @(Get-ChildItem -LiteralPath $item.FullName -File -Recurse -Force) } else { @($item) }
        $record.Files = @($files | ForEach-Object {
            $target = if ($item.PSIsContainer) { $entry.Destination + $_.FullName.Substring($item.FullName.Length) } else { $entry.Destination }
            [pscustomobject]@{ Source=$_.FullName; Destination=$target; Bytes=$_.Length; SHA256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash }
        })
        [IO.Directory]::CreateDirectory((Split-Path -Parent $entry.Destination)) | Out-Null
        Move-Item -LiteralPath $entry.Source -Destination $entry.Destination -ErrorAction Stop
        foreach ($file in $record.Files) {
            if (!(Test-Path -LiteralPath $file.Destination) -or (Get-FileHash -LiteralPath $file.Destination -Algorithm SHA256).Hash -ne $file.SHA256) {
                throw "Archive verification failed: $($file.Destination)"
            }
        }
        $record.Status='moved-and-hash-verified'
    } catch {
        $record.Status='kept-or-failed'
        $record.Error=$_.Exception.Message
    }
    $result=[pscustomobject]@{ Date='2026-11-07'; Workspace=$workspaceRoot; ProtectedBefore=$protectedBefore; Entries=$journal.ToArray() }
    [IO.File]::WriteAllText($manifestPath, ($result | ConvertTo-Json -Depth 8), [Text.UTF8Encoding]::new($false))
}
foreach ($relative in $protected) {
    if ((Get-FileHash -LiteralPath (Join-Path $repoRoot $relative) -Algorithm SHA256).Hash -ne $protectedBefore[$relative]) {
        throw "Active file changed unexpectedly: $relative"
    }
}
$moved = @($journal | Where-Object Status -eq 'moved-and-hash-verified')
$skipped = @($journal | Where-Object Status -ne 'moved-and-hash-verified')
[pscustomobject]@{ MovedEntries=$moved.Count; VerifiedFiles=($moved.Files | Measure-Object).Count; Bytes=($moved.Files | Measure-Object Bytes -Sum).Sum; ProtectedFilesUnchanged=$protected.Count; Manifest=$manifestPath; Exceptions=$skipped } | ConvertTo-Json -Depth 5
