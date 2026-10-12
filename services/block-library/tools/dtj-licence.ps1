# DTJ licence switch: hide, show or check the DTJ blocks of a store with ONE short command (it asks for the secrets for you).
#
#   tools\dtj-licence hide                 hide all three apps' blocks on the test store
#   tools\dtj-licence show                 show them again
#   tools\dtj-licence status               only read the flags (changes nothing)
#   tools\dtj-licence hide -App sections   only one app: blocks, sections or sections2
#
# Each app has its OWN client secret (Shopify issues no master key). A secret is typed hidden, kept only in this window's memory while the
# script runs, never written to a file, never printed, and removed from the window when the script ends.
# Changing the flag is a tier 2 action: YOU run this, nothing runs it for you.
param(
    [Parameter(Mandatory = $true, Position = 0)][ValidateSet('status', 'hide', 'show')][string]$Action,
    [ValidateSet('all', 'blocks', 'sections', 'sections2')][string]$App = 'all',
    [string]$Shop = 'elevate-with-harsh.myshopify.com',
    [string]$ApprovedBy = 'Harsh',
    [switch]$DryRun   # print the exact command instead of running it (no secret is shown, nothing is sent)
)
$ErrorActionPreference = 'Stop'

$tools = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $tools '..\..\..\.work\.venv\Scripts\python.exe'
$tool = Join-Path $tools 'licence.py'
if (-not (Test-Path $python)) { throw "Python not found at $python (the project's .work\.venv is missing)." }

$secretVars = [ordered]@{ blocks = 'DTJ_BLOCKS_CLIENT_SECRET'; sections = 'DTJ_SECTIONS_CLIENT_SECRET'; sections2 = 'DTJ_SECTIONS2_CLIENT_SECRET' }
$apps = if ($App -eq 'all') { @($secretVars.Keys) } else { @($App) }
$niceName = @{ blocks = 'DTJ Blocks'; sections = 'DTJ Sections'; sections2 = 'DTJ Sections 2' }

# an explicit string array: a one-item result (status) would otherwise collapse into a plain string and the action word got lost
[string[]]$actionArgs = @()
if ($Action -eq 'status') { $actionArgs = @('--status') }
elseif ($Action -eq 'hide') { $actionArgs = @('--set', 'inactive', '--approved-by', $ApprovedBy) }
else { $actionArgs = @('--set', 'active', '--approved-by', $ApprovedBy) }

$failed = @()
try {
    foreach ($a in $apps) {
        $var = $secretVars[$a]
        Write-Host ""
        Write-Host "== $($niceName[$a]) ($Action on $Shop)" -ForegroundColor Cyan
        $secret = [Environment]::GetEnvironmentVariable($var, 'Process')
        if (-not $secret) {
            $typed = Read-Host "Client secret of $($niceName[$a]) (Dev Dashboard > that app > Settings; typed hidden)" -AsSecureString
            $secret = [System.Net.NetworkCredential]::new('', $typed).Password
        }
        $secret = $secret.Trim()
        # a client secret looks like shpss_ followed by letters and digits; anything else (a pasted command, a client id) would only give a confusing HTTP 400
        if ($secret -notmatch '^shpss_[0-9a-f]{20,}$') {
            Write-Host "That does not look like a client secret (it should start with shpss_). Skipping $($niceName[$a])." -ForegroundColor Yellow
            $failed += $a
            continue
        }
        Set-Item -Path "Env:$var" -Value $secret
        [string[]]$argList = @($tool, '--shop', $Shop) + $actionArgs + @('--app', $a)
        if ($DryRun) {
            Write-Host "DRY RUN: python $($argList -join ' ')" -ForegroundColor DarkGray
            $global:LASTEXITCODE = 0
        }
        else {
            & $python $argList
        }
        if ($LASTEXITCODE -ne 0) {
            $failed += $a
            if ($LASTEXITCODE -eq 1) {
                Write-Host "If the message above says HTTP 400, the secret is not the one of $($niceName[$a]): copy it again from THAT app's Settings page." -ForegroundColor Yellow
            }
        }
        Remove-Item -Path "Env:$var" -ErrorAction SilentlyContinue
        $secret = $null
    }
}
finally {
    foreach ($v in $secretVars.Values) { Remove-Item -Path "Env:$v" -ErrorAction SilentlyContinue }
}

Write-Host ""
if ($failed.Count -gt 0) {
    Write-Host "Not done for: $($failed -join ', ')" -ForegroundColor Red
    exit 1
}
Write-Host "Done: $Action for $($apps -join ', ')." -ForegroundColor Green
