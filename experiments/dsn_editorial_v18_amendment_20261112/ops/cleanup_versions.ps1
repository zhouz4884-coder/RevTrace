$ErrorActionPreference = 'Stop'
$recordRoot = Split-Path -Parent $PSScriptRoot
$keepNames = @('20261105_dsn2027_release_v15','20261111_dsn2027_release_v16','20261111_dsn2027_release_v17','20261112_dsn2027_release_v18')
$namedRoots = @(
 'D:\VLA_QWEN\RevTrace\Paper_DSN\revisions',
 'C:\Users\LENOVO\.codex\worktrees\revtrace-dsn-evidence\RevTrace\Paper_DSN\revisions',
 'C:\Users\LENOVO\.codex\worktrees\revtrace-dsn-v18-writing\RevTrace\Paper_DSN\revisions',
 'C:\Users\LENOVO\.codex\worktrees\revtrace-dsn-v16-writing\RevTrace\Paper_DSN\revisions'
)
$plans = @()
foreach ($namedRoot in $namedRoots) {
 if (-not (Test-Path -LiteralPath $namedRoot -PathType Container)) { continue }
 $revisionRoot = (Resolve-Path -LiteralPath $namedRoot).ProviderPath.TrimEnd('\')
 if (-not [string]::Equals($revisionRoot,[IO.Path]::GetFullPath($namedRoot).TrimEnd('\'),[StringComparison]::OrdinalIgnoreCase)) { throw 'Unexpected root resolution' }
 foreach ($directory in Get-ChildItem -LiteralPath $revisionRoot -Directory -Force) {
  if ($keepNames -contains $directory.Name) { continue }
  if ($directory.Name -notmatch '^([0-9]{8})_' -or [int]$Matches[1] -ge 20261105) { throw ('Unclassified revision: '+$directory.FullName) }
  $absoluteTarget = (Resolve-Path -LiteralPath $directory.FullName).ProviderPath
  if (-not $absoluteTarget.StartsWith($revisionRoot+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Target escaped revision root' }
  if (-not [string]::Equals((Split-Path -Parent $absoluteTarget),$revisionRoot,[StringComparison]::OrdinalIgnoreCase)) { throw 'Target is not a direct revision child' }
  $children = @(Get-ChildItem -LiteralPath $absoluteTarget -Recurse -Force)
  if (($directory.Attributes -band [IO.FileAttributes]::ReparsePoint) -or @($children | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }).Count) { throw 'Reparse point requires separate handling' }
  $files = @($children | Where-Object { -not $_.PSIsContainer })
  $plans += [pscustomobject]@{ revision_root=$revisionRoot; target=$absoluteTarget; name=$directory.Name; files=$files.Count; bytes=[long](($files | Measure-Object -Property Length -Sum).Sum) }
 }
}
$planRecord = [pscustomobject]@{ record_type='USER_AUTHORIZED_PAPER_VERSION_CLEANUP'; keep=$keepNames; targets=$plans; experiment_data_touched=$false; git_history_rewritten=$false }
$planRecord | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath (Join-Path $recordRoot 'CLEANUP_PLAN.json') -Encoding utf8
foreach ($entry in $plans) {
 $checkedTarget = (Resolve-Path -LiteralPath $entry.target).ProviderPath
 if (-not [string]::Equals($checkedTarget,$entry.target,[StringComparison]::OrdinalIgnoreCase) -or -not $checkedTarget.StartsWith($entry.revision_root+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Target changed after inspection' }
 Remove-Item -LiteralPath $checkedTarget -Recurse -Force
 if (Test-Path -LiteralPath $checkedTarget) { throw 'Revision removal incomplete' }
}
$remaining = @()
foreach ($namedRoot in $namedRoots) {
 if (-not (Test-Path -LiteralPath $namedRoot -PathType Container)) { continue }
 $names = @(Get-ChildItem -LiteralPath $namedRoot -Directory -Force | Select-Object -ExpandProperty Name)
 if (@($names | Where-Object { $keepNames -notcontains $_ }).Count) { throw 'Unexpected remaining revision' }
 $remaining += [pscustomobject]@{ root=$namedRoot; versions=$names }
}
if (@($remaining[0].versions).Count -ne 4) { throw 'Main workspace must retain all four requested versions' }
$receipt = [pscustomobject]@{ status='PASS_OLDER_PAPER_REVISIONS_REMOVED_ONLY_V15_V18_RETAINED'; removed_directories=$plans.Count; remaining=$remaining; experiment_data_touched=$false; git_history_rewritten=$false }
$receipt | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath (Join-Path $recordRoot 'CLEANUP_RECEIPT.json') -Encoding utf8
$receipt | ConvertTo-Json -Depth 7 -Compress
