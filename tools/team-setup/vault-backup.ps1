<#
Sign in to DTJ's Bitwarden vault on this laptop, back up this laptop's store-factory keys into it, fetch the ones only the vault has,
and show the result (key names only). Running it again is safe: keys already in the vault are left as they are.

  In the project folder, in PowerShell (Claude can open it for you in its Terminal panel):
      powershell -ExecutionPolicy Bypass -File tools\team-setup\vault-backup.ps1

You type only what Bitwarden asks: your email, your master password (hidden) and the two-step or new-device code if it asks.
The session key Bitwarden gives back stays inside this window and is never shown. Values never appear on screen.
#>
$ErrorActionPreference = 'Stop'
$Repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $Repo
# a window opened before the Bitwarden tool was installed cannot see it: read the PATH again
$env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
if (-not (Get-Command bw -ErrorAction SilentlyContinue)) {
  Write-Host 'Installing the Bitwarden command-line tool...'
  npm install -g '@bitwarden/cli'
  $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
}

$state = ''
try { $state = (bw status | ConvertFrom-Json).status } catch { $state = '' }
# Bitwarden writes its questions to the screen (stderr) and only the session key to the output, so it can be kept here unseen
if ($state -eq 'unauthenticated') {
  Write-Host ''
  Write-Host 'Sign in to DTJ''s Bitwarden: your email, then your master password (nothing shows while you type),' -ForegroundColor Cyan
  Write-Host 'then the code Bitwarden asks for (two-step login, or the new-device code sent to your email).' -ForegroundColor Cyan
  $env:BW_SESSION = (bw login --raw)
} elseif ($state -ne 'unlocked') {
  Write-Host ''
  Write-Host 'Unlock Bitwarden: type your master password (nothing shows while you type).' -ForegroundColor Cyan
  $env:BW_SESSION = (bw unlock --raw)
  if (-not $env:BW_SESSION) {
    # a master password changed in the web vault leaves this laptop's copy locked with the old one: sign in afresh
    Write-Host ''
    Write-Host 'That did not unlock (a mistyped or recently changed master password). Signing in afresh:' -ForegroundColor Cyan
    Write-Host 'your email, your master password, and the code if Bitwarden asks for one.' -ForegroundColor Cyan
    bw logout | Out-Null
    $env:BW_SESSION = (bw login --raw)
  }
}
if (-not $env:BW_SESSION -and $state -ne 'unlocked') { throw 'Bitwarden did not sign in, so nothing was changed. Run this again.' }

Write-Host ''
Write-Host '== 1/3 Backing up this laptop''s keys into the vault' -ForegroundColor Cyan
python tools\team-setup\vault.py push --all
Write-Host ''
Write-Host '== 2/3 Fetching the keys only the vault has' -ForegroundColor Cyan
python tools\team-setup\vault.py pull
Write-Host ''
Write-Host '== 3/3 Result (names only)' -ForegroundColor Cyan
python tools\team-setup\vault.py status
$env:BW_SESSION = $null
Write-Host ''
Write-Host 'Done. You can close this tab.' -ForegroundColor Yellow
