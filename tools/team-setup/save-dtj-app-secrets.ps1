<#
Harsh only (once): save the client secrets of DTJ's ORIGINAL apps (DTJ Blocks, DTJ Sections, DTJ Sections 2) in your Windows user
settings, so the install service can switch them on stores in DTJ's own Shopify organization (for example elevate-with-harsh).

  In the project folder, in PowerShell (signed in to the Shopify CLI with the account that owns the apps):
      powershell -ExecutionPolicy Bypass -File tools\team-setup\save-dtj-app-secrets.ps1

Each secret is read straight from Shopify's CLI (`shopify app env show`) and saved without ever being shown on screen. If the CLI
cannot read one, you can paste it into a hidden prompt instead (from the app's page in the Shopify Dev Dashboard, Client credentials).
Saved as DTJ_BLOCKS_CLIENT_SECRET, DTJ_SECTIONS_CLIENT_SECRET and DTJ_SECTIONS2_CLIENT_SECRET (the names services/install-catcher/
tools/deploy.py and services/block-library/tools/licence.py read). Never paste them into a chat, an email or a file.

A NEW CLIENT's own app copies (skill dtj-add-shop): their three secrets, asked one by one, checked the same way:
      powershell -ExecutionPolicy Bypass -File tools\team-setup\save-dtj-app-secrets.ps1 -Client royal-dosa
saves DTJ_SECRET_ROYAL_DOSA_BLOCKS / _SECTIONS / _SECTIONS2 (the names services/install-catcher/tools/deploy.py reads).
#>
param([switch]$Paste, [string]$Client = '')  # -Paste: skip the Shopify CLI; -Client <short name>: a client's app copies
$ErrorActionPreference = 'Stop'
$Repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $Repo

$apps = @(
  @{ Var = 'DTJ_BLOCKS_CLIENT_SECRET';    Path = 'services\block-library';            Label = 'DTJ Blocks' },
  @{ Var = 'DTJ_SECTIONS_CLIENT_SECRET';  Path = 'services\block-library-sections';   Label = 'DTJ Sections' },
  @{ Var = 'DTJ_SECTIONS2_CLIENT_SECRET'; Path = 'services\block-library-sections-2'; Label = 'DTJ Sections 2' }
)
$which = 'the original app'
if ($Client) {
  if ($Client -notmatch '^[a-z0-9]+(-[a-z0-9]+)*$') { throw "-Client must be the client's short name: lowercase letters, digits and single dashes" }
  $up = ($Client.ToUpper() -replace '[^A-Z0-9]', '_')
  $apps = @(
    @{ Var = "DTJ_SECRET_${up}_BLOCKS";    Label = "DTJ Blocks - (this client)" },
    @{ Var = "DTJ_SECRET_${up}_SECTIONS";  Label = "DTJ Sections - (this client)" },
    @{ Var = "DTJ_SECRET_${up}_SECTIONS2"; Label = "DTJ Sections 2 - (this client)" }
  )
  $which = "the client's copy you created"
  $Paste = $true  # a new copy has no linked config here yet: ask straight away
}
foreach ($a in $apps) {
  Write-Host ''
  Write-Host "$($a.Label) -> $($a.Var)" -ForegroundColor Cyan
  $plain = $null
  if (-not $Paste) { try {
    # the CLI prints SHOPIFY_API_SECRET=...; it is captured here and never written to the screen. It runs as a background job with
    # a 90-second limit, so a login question it cannot ask (no screen) never leaves this window waiting.
    $job = Start-Job -ScriptBlock { param($p) & shopify app env show --path $p --config shopify.app.toml 2>&1 | Out-String } -ArgumentList (Join-Path $Repo $a.Path)
    if (Wait-Job $job -Timeout 90) { $out = Receive-Job $job | Out-String } else { Stop-Job $job; $out = '' }
    Remove-Job $job -Force
    $m = [regex]::Match($out, 'SHOPIFY_API_SECRET\s*=\s*([^\s\x1b]+)')
    if ($m.Success) { $plain = $m.Groups[1].Value.Trim() }
    $out = $null
  } catch { $plain = $null } }
  # a Shopify client secret is shpss_ + 32 hex characters (the Client ID is 32 hex characters with no prefix: a common mix-up)
  for ($try = 1; $try -le 3 -and -not ($plain -and $plain.Trim() -match '^shpss_[0-9a-f]{32}$'); $try++) {
    if ($plain) { Write-Host 'That is not a client secret (it must start with shpss_ and be 38 characters; the Client ID is not it). Try again.' -ForegroundColor Red }
    elseif (-not $Paste) { Write-Host 'The Shopify CLI could not read it (not signed in with the account that owns the app?).' }
    Write-Host "In the Dev Dashboard open $($a.Label) ($which), Settings > Client credentials, copy the Secret."
    $secure = Read-Host 'Paste the client secret here and press Enter (nothing shows; leave empty to skip)' -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try { $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
    if ([string]::IsNullOrWhiteSpace($plain)) { break }
  }
  if ([string]::IsNullOrWhiteSpace($plain) -or $plain.Trim() -notmatch '^shpss_[0-9a-f]{32}$') { Write-Host "Skipped $($a.Var) (nothing saved)."; continue }
  $plain = $plain.Trim()
  [Environment]::SetEnvironmentVariable($a.Var, $plain, 'User')
  Write-Host "Saved $($a.Var) ($($plain.Length) characters)."
  $plain = $null
}
Write-Host ''
Write-Host 'Done. Tell Claude "saved the app secrets": it checks them with a read-only status call and then adds the store to the switch.' -ForegroundColor Yellow
