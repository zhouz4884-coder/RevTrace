param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Z0-9_]+$')]
    [string]$ExperimentId,

    [Parameter(Mandatory = $true)]
    [ValidateSet('phase2', 'phase3', 'phase4', 'phase5')]
    [string]$Phase
)

$repoRoot = Split-Path -Parent $PSScriptRoot
$target = Join-Path $repoRoot "results\$Phase\$($ExperimentId.ToLower())"

if (Test-Path -LiteralPath $target) {
    throw "Experiment directory already exists: $target"
}

New-Item -ItemType Directory -Path $target | Out-Null
New-Item -ItemType Directory -Path (Join-Path $target "tables") | Out-Null
New-Item -ItemType Directory -Path (Join-Path $target "manifests") | Out-Null

$run = [ordered]@{
    schema_version = 1
    experiment_id = $ExperimentId
    phase = $Phase
    status = "PLANNED"
    git_commit = ""
    config = ""
    raw_result_root = ""
    log_root = ""
    environment_record = ""
    workload_manifest_sha256 = ""
    gate_decision = "PENDING"
}

$json = $run | ConvertTo-Json -Depth 5
[System.IO.File]::WriteAllText(
    (Join-Path $target "RUN.json"),
    $json + "`n",
    [System.Text.UTF8Encoding]::new($false)
)

Write-Output $target
