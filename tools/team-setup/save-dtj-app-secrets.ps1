<#
Harsh only (once): save the client secrets of DTJ's ORIGINAL apps (DTJ Blocks, DTJ Sections, DTJ Sections 2) in your Windows user
settings, so the install service can switch them on stores in DTJ's own Shopify organization (for example elevate-with-harsh).

  In the project folder, in PowerShell (signed in to the Shopify CLI with the account that owns the apps):
      powershell -ExecutionPolicy Bypass -File tools\team-setup\save-dtj-app-secrets.ps1

Each secret is read straight from Shopify's CLI (`shopify app env show`) and saved without ever being shown on screen. If the CLI
cannot read one, you can paste it into a hidden prompt instead (from the app's page in the Shopify Dev Dashboard, Client credentials).
Saved as DTJ_BLOCKS_CLIENT_SECRET, DTJ_SECTIONS_CLIENT_SECRET and DTJ_SECTIONS2_CLIENT_SECRET (the names services/install-catcher/
tools/deploy.py and services/block-library/tools/licence.py read). Never paste them into a chat, an email or a file.
#>
$ErrorActionPreference = 'Stop'
$Repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $Repo

$apps = @(
  @{ Var = 'DTJ_BLOCKS_CLIENT_SECRET';    Path = 'services\block-library';            Label = 'DTJ Blocks' },
  @{ Var = 'DTJ_SECTIONS_CLIENT_SECRET';  Path = 'services\block-library-sections';   Label = 'DTJ Sections' },
  @{ Var = 'DTJ_SECTIONS2_CLIENT_SECRET'; Path = 'services\block-library-sections-2'; Label = 'DTJ Sections 2' }
)
foreach ($a in $apps) {
  Write-Host ''
  Write-Host "$($a.Label) -> $($a.Var)" -ForegroundColor Cyan
  $plain = $null
  try {
    # the CLI prints SHOPIFY_API_SECRET=...; it is captured here and never written to the screen. It runs as a background job with
    # a 90-second limit, so a login question it cannot ask (no screen) never leaves this window waiting.
    $job = Start-Job -ScriptBlock { param($p) & shopify app env show --path $p --config shopify.app.toml 2>&1 | Out-String } -ArgumentList (Join-Path $Repo $a.Path)
    if (Wait-Job $job -Timeout 90) { $out = Receive-Job $job | Out-String } else { Stop-Job $job; $out = '' }
    Remove-Job $job -Force
    $m = [regex]::Match($out, 'SHOPIFY_API_SECRET\s*=\s*([^\s\x1b]+)')
    if ($m.Success) { $plain = $m.Groups[1].Value.Trim() }
    $out = $null
  } catch { $plain = $null }
  if (-not $plain) {
    Write-Host 'The Shopify CLI could not read it (not signed in with the account that owns the app?).'
    $secure = Read-Host 'Paste the client secret here instead and press Enter (nothing shows; leave empty to skip)' -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try { $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
  }
  if ([string]::IsNullOrWhiteSpace($plain)) { Write-Host "Skipped $($a.Var)."; continue }
  $plain = $plain.Trim()
  [Environment]::SetEnvironmentVariable($a.Var, $plain, 'User')
  Write-Host "Saved $($a.Var) ($($plain.Length) characters)."
  $plain = $null
}
Write-Host ''
Write-Host 'Done. Tell Claude "saved the app secrets": it checks them with a read-only status call and then adds the store to the switch.' -ForegroundColor Yellow
