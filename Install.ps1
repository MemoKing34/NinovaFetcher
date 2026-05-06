<#
.SYNOPSIS
  Installs/ensures Python + Git (via winget), lets user pick a directory (default: Documents),
  clones https://github.com/MemoKing34/NinovaFetcher.git, and optionally runs run.bat (default Yes).

.NOTES
  - Works in Windows PowerShell 5.1 and PowerShell 7+
  - Uses winget when python/git are missing
  - If installers don't add PATH automatically, this script adds common install dirs to the *user* PATH
  - This script was written by ChatGPT (OpenAI) for the user upon request.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Test-CommandInPath {
  param([Parameter(Mandatory)][string]$Command)
  try {
    $null = Get-Command $Command -ErrorAction Stop
    return $true
  } catch {
    return $false
  }
}

function Refresh-ProcessPath {
  $machine = [Environment]::GetEnvironmentVariable('Path', 'Machine')
  $user = [Environment]::GetEnvironmentVariable('Path', 'User')
  if ($null -eq $machine) { $machine = "" }
  if ($null -eq $user) { $user = "" }
  $env:Path = $machine + ';' + $user
}

function Add-ToUserPathIfMissing {
  param([Parameter(Mandatory)][string]$Dir)

  if (-not (Test-Path -LiteralPath $Dir)) { return $false }

  $currentUserPath = [Environment]::GetEnvironmentVariable('Path', 'User')
  if ($null -eq $currentUserPath) { $currentUserPath = "" }

  $parts = $currentUserPath -split ';' | Where-Object { $_ -and $_.Trim() -ne "" }
  $normalizedParts = $parts | ForEach-Object { $_.Trim().TrimEnd('\') }
  $normalizedDir = $Dir.Trim().TrimEnd('\')

  if ($normalizedParts -contains $normalizedDir) {
    return $false
  }

  $newPath = if ([string]::IsNullOrWhiteSpace($currentUserPath)) { $Dir } else { "$currentUserPath;$Dir" }
  [Environment]::SetEnvironmentVariable('Path', $newPath, 'User')

  Refresh-ProcessPath
  return $true
}

function Ensure-Winget {
  if (-not (Test-CommandInPath "winget")) {
    throw "winget was not found in PATH. Please install/update 'App Installer' from Microsoft Store, then re-run this script."
  }
}

function Install-PythonIfNeeded {
  if (Test-CommandInPath "python") { return }

  Ensure-Winget
  Write-Host "Python not found. Installing Python via winget..." -ForegroundColor Yellow

  # Generic current Python 3 package
  winget install --id Python.Python.3 -e --silent --accept-package-agreements --accept-source-agreements | Out-Host

  Start-Sleep -Seconds 2
  Refresh-ProcessPath

  if (Test-CommandInPath "python") { return }

  Write-Host "Python still not found in PATH after install. Attempting to add common install locations to USER PATH..." -ForegroundColor Yellow

  # Include future-friendly versions (3.15, 3.14) plus common older ones
  $pythonVersions = @("315","314","313","312","311","310","39","38")  # newest-first

  $candidateDirs = @(
    foreach ($v in $pythonVersions) {
      Join-Path $env:LOCALAPPDATA "Programs\Python\Python$v\"
      Join-Path $env:LOCALAPPDATA "Programs\Python\Python$v\Scripts\"
      Join-Path $env:USERPROFILE  "AppData\Local\Programs\Python\Python$v\"
      Join-Path $env:USERPROFILE  "AppData\Local\Programs\Python\Python$v\Scripts\"
    }
  ) | Select-Object -Unique

  foreach ($dir in $candidateDirs) {
    if (Test-Path -LiteralPath $dir) {
      Add-ToUserPathIfMissing -Dir $dir | Out-Null
    }
  }

  if (-not (Test-CommandInPath "python")) {
    throw "Python installation completed, but 'python' is still not available in PATH. Try opening a new terminal, or verify Python was installed."
  }
}

function Install-GitIfNeeded {
  if (Test-CommandInPath "git") { return }

  Ensure-Winget
  Write-Host "Git not found. Installing Git via winget..." -ForegroundColor Yellow

  winget install --id Git.Git -e --silent --accept-package-agreements --accept-source-agreements | Out-Host

  Start-Sleep -Seconds 2
  Refresh-ProcessPath

  if (Test-CommandInPath "git") { return }

  Write-Host "Git still not found in PATH after install. Attempting to add common Git locations to USER PATH..." -ForegroundColor Yellow

  $candidateDirs = @(
    "C:\Program Files\Git\cmd"
    "C:\Program Files\Git\bin"
    "C:\Program Files (x86)\Git\cmd"
    "C:\Program Files (x86)\Git\bin"
  ) | Select-Object -Unique

  foreach ($dir in $candidateDirs) {
    if (Test-Path -LiteralPath $dir) {
      Add-ToUserPathIfMissing -Dir $dir | Out-Null
    }
  }

  if (-not (Test-CommandInPath "git")) {
    throw "Git installation completed, but 'git' is still not available in PATH. Try opening a new terminal, or verify Git was installed."
  }
}

function Select-FolderDialogOrDefault {
  param([Parameter(Mandatory)][string]$DefaultPath)

  try {
    Add-Type -AssemblyName System.Windows.Forms -ErrorAction Stop
    $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $dialog.Description = "Choose a folder where NinovaFetcher will be cloned."
    $dialog.SelectedPath = $DefaultPath
    $dialog.ShowNewFolderButton = $true

    $result = $dialog.ShowDialog()
    if ($result -eq [System.Windows.Forms.DialogResult]::OK -and -not [string]::IsNullOrWhiteSpace($dialog.SelectedPath)) {
      return $dialog.SelectedPath
    }
  } catch {
    # Ignore GUI errors and fall back
  }

  return $DefaultPath
}

function Read-YesNoDefaultYes {
  param([Parameter(Mandatory)][string]$Prompt)

  while ($true) {
    $ans = Read-Host "$Prompt [Y/n]"
    if ([string]::IsNullOrWhiteSpace($ans)) { return $true }
    switch ($ans.Trim().ToLowerInvariant()) {
      'y' { return $true }
      'yes' { return $true }
      'n' { return $false }
      'no' { return $false }
      default { Write-Host "Please answer Y or N (or press Enter for Yes)." -ForegroundColor Yellow }
    }
  }
}

# ------------------- Main -------------------

Install-PythonIfNeeded
Write-Host "Python OK: $((python --version) 2>&1)" -ForegroundColor Green

Install-GitIfNeeded
Write-Host "Git OK: $((git --version) 2>&1)" -ForegroundColor Green

# Choose directory (default under Documents)
$documents = [Environment]::GetFolderPath('MyDocuments')
if ([string]::IsNullOrWhiteSpace($documents)) {
  $documents = Join-Path $env:USERPROFILE "Documents"
}

# This is just the default directory the dialog opens to / fallback uses.
$defaultCloneRoot = Join-Path $documents "NinovaFetcher-Workspace"

$targetRoot = Select-FolderDialogOrDefault -DefaultPath $defaultCloneRoot

if (-not (Test-Path -LiteralPath $targetRoot)) {
  New-Item -ItemType Directory -Path $targetRoot -Force | Out-Null
}

# Clone repo under chosen dir
$repoUrl  = "https://github.com/MemoKing34/NinovaFetcher.git"
$repoName = "NinovaFetcher"
$repoPath = Join-Path $targetRoot $repoName

if (Test-Path -LiteralPath $repoPath) {
  Write-Host "Repo directory already exists: $repoPath" -ForegroundColor Yellow
  $pull = Read-YesNoDefaultYes -Prompt "Directory exists. Do you want to run 'git pull' to update it?"
  if ($pull) {
    Push-Location $repoPath
    try {
      git pull | Out-Host
    } finally {
      Pop-Location
    }
  }
} else {
  Write-Host "Cloning $repoUrl into $repoPath ..." -ForegroundColor Cyan
  git clone $repoUrl $repoPath | Out-Host
}

if (-not (Test-Path -LiteralPath $repoPath)) {
  throw "Repo path does not exist after clone/update: $repoPath"
}

Set-Location $repoPath

# Ask to run (default Yes) and run run.bat
$run = Read-YesNoDefaultYes -Prompt "Run NinovaFetcher now (run.bat)?"
if ($run) {
  $bat = Join-Path $repoPath "run.bat"
  if (-not (Test-Path -LiteralPath $bat)) {
    throw "run.bat not found at: $bat"
  }

  Write-Host "Starting: $bat" -ForegroundColor Cyan
  Start-Process -FilePath $bat -WorkingDirectory $repoPath
} else {
  Write-Host "Skipped running NinovaFetcher." -ForegroundColor Yellow
}