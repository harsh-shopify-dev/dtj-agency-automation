<#
DTJ page design: set up this laptop. Run it once (running it again is safe: it only adds what is missing).

  In the project folder, in PowerShell:
      powershell -ExecutionPolicy Bypass -File tools\team-setup\setup-team-pc.ps1
  To type a secret again (for example a new password):
      powershell -ExecutionPolicy Bypass -File tools\team-setup\setup-team-pc.ps1 -Replace

What it does:
  1. installs Git, Python, Node.js and Google Chrome if they are missing (asks first)
  2. installs Shopify's command-line tool and the Python packages
  3. connects Claude Code in this folder to DTJ's n8n
  4. asks for YOUR secret settings: typed into a hidden prompt, saved only in your Windows user settings, never shown, never
     written to a file
  5. runs the readiness check (tools\team-setup\check_setup.py)
It never changes anything on a Shopify store.
#>
param([switch]$Replace)
$ErrorActionPreference = 'Stop'
$Repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $Repo

function Say($text) { Write-Host ''; Write-Host "== $text" -ForegroundColor Cyan }
function Has($cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }
function Refresh-Path {
  $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
}
function Python-Ok {
  # the Microsoft Store 'python' shortcut is not Python: ask for the version instead of trusting the name
  try { $v = (& python --version 2>&1) | Out-String; return ($v -match 'Python 3\.(1[1-9]|[2-9][0-9])') } catch { return $false }
}

Say '1/5 Programs'
$missing = @()
if (-not (Has 'git')) { $missing += @{ Id = 'Git.Git'; Name = 'Git' } }
if (-not (Python-Ok)) { $missing += @{ Id = 'Python.Python.3.13'; Name = 'Python 3.13' } }
if (-not (Has 'node')) { $missing += @{ Id = 'OpenJS.NodeJS.LTS'; Name = 'Node.js' } }
$browser = (Test-Path "$env:ProgramFiles\Google\Chrome\Application\chrome.exe") -or
           (Test-Path "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe") -or
           (Test-Path "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe") -or
           (Test-Path "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe")
if (-not $browser) { $missing += @{ Id = 'Google.Chrome'; Name = 'Google Chrome' } }
if ($missing.Count -eq 0) {
  Write-Host 'All programs are already installed.'
} else {
  if (-not (Has 'winget')) { throw "Windows 'App Installer' (winget) is missing. Install 'App Installer' from the Microsoft Store, then run this again." }
  Write-Host ('These will be installed: ' + (($missing | ForEach-Object { $_.Name }) -join ', '))
  $answer = Read-Host 'Type Y and press Enter to install them'
  if ($answer -notmatch '^[Yy]$') { throw 'Stopped: nothing was installed.' }
  foreach ($m in $missing) { winget install --id $m.Id -e --accept-source-agreements --accept-package-agreements }
  Refresh-Path
  if (-not (Python-Ok)) { throw 'Python was installed but this window cannot see it yet. Close PowerShell, open a NEW window and run this script again.' }
}

Say '2/5 Shopify CLI and Python packages'
if (-not (Has 'shopify')) { npm install -g '@shopify/cli@latest'; Refresh-Path }
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r services\store-builder\requirements.txt
Write-Host 'Done.'

Say '3/5 Connect Claude Code (in this folder) to n8n'
if (-not (Test-Path '.mcp.json')) { Copy-Item '.mcp.example.json' '.mcp.json'; Write-Host 'Created .mcp.json (it holds no secret).' }
else { Write-Host '.mcp.json is already there.' }
# allow the project's n8n server without a question the first time Claude Code opens this folder
python -c "import json,pathlib; p=pathlib.Path('.claude/settings.local.json'); d=json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}; s=d.setdefault('enabledMcpjsonServers', []); s.append('n8n') if 'n8n' not in s else None; p.write_text(json.dumps(d, indent=2), encoding='utf-8'); print('Claude Code will use the n8n server in this folder.')"

Say '4/5 Your secret settings'
Write-Host 'Each one is typed into a hidden prompt (nothing shows while you paste), saved only in your Windows user settings.'
Write-Host 'Never paste these into a chat, an email or a file.'
function Save-Secret([string]$Name) {
  if ($Name -eq 'N8N_MCP_TOKEN') {
    $help = 'Your n8n access token. In n8n (https://n8n.srv2048145.hstgr.cloud) open Settings > MCP Access and create or copy your token. No n8n login yet? Ask Harsh for an invite.'
  } else {
    $shop = ($Name -replace '^DTJ_THEME_ACCESS_', '').ToLower().Replace('_', '-')
    $help = "The Theme Access password for the shop '$shop'. Harsh (or the shop owner) sends it from Shopify admin > Apps > Theme Access; it arrives by email."
  }
  Write-Host ''
  Write-Host "$Name" -ForegroundColor Yellow
  Write-Host $help
  $secure = Read-Host 'Paste it here and press Enter (leave empty to skip)' -AsSecureString
  $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
  try { $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
  if ([string]::IsNullOrWhiteSpace($plain)) { Write-Host "Skipped $Name."; return }
  $plain = $plain.Trim()
  [Environment]::SetEnvironmentVariable($Name, $plain, 'User')
  Set-Item -Path "env:$Name" -Value $plain
  Write-Host "Saved $Name ($($plain.Length) characters)."
  $plain = $null
}
# the company vault first (Bitwarden): one sign-in copies every shared key this person may see (docs/ACCESS-AND-KEYS.md)
Write-Host ''
$useVault = Read-Host 'Has Harsh given you access to DTJ''s Bitwarden vault? Type Y to sign in and copy your keys from it (Enter = skip)'
if ($useVault -match '^[Yy]$') {
  if (-not (Has 'bw')) { npm install -g '@bitwarden/cli'; Refresh-Path }
  $bwState = ''
  try { $bwState = (bw status | ConvertFrom-Json).status } catch { $bwState = '' }
  if ($bwState -eq 'unauthenticated') {
    Write-Host 'Sign in to Bitwarden: your email, then your master password (hidden), then the code if it asks for one.'
    $env:BW_SESSION = (bw login --raw)  # only the session key comes back; it stays in this window and is never shown
  }
  python tools\team-setup\vault.py pull @(if ($Replace) { '--replace' })
}
# the n8n token is personal (never in the vault): the list of shops comes from n8n
if ($Replace -or -not [Environment]::GetEnvironmentVariable('N8N_MCP_TOKEN', 'User')) { Save-Secret 'N8N_MCP_TOKEN' }
if ($Replace) {
  $shops = @(python tools\team-setup\check_setup.py --secret-names) | Where-Object { $_ -and $_ -ne 'N8N_MCP_TOKEN' }
} else {
  $shops = @(python tools\team-setup\check_setup.py --missing-secrets) | Where-Object { $_ -and $_ -ne 'N8N_MCP_TOKEN' }
}
if ($shops.Count -eq 0) { Write-Host 'Every shop password is already saved.' }
foreach ($n in $shops) { Save-Secret $n }

Say '5/5 Readiness check'
python tools\team-setup\check_setup.py
Write-Host ''
Write-Host 'IMPORTANT: close Claude and this window, then open them again, so they see the new settings.' -ForegroundColor Yellow
