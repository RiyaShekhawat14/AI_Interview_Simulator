param(
  [int]$Port = 8000,
  [switch]$Reload,
  [switch]$KillExisting,
  [switch]$AllowExisting
)

function Test-PortOpen {
  param([int]$TargetPort)

  $client = New-Object System.Net.Sockets.TcpClient
  try {
    $async = $client.BeginConnect("127.0.0.1", $TargetPort, $null, $null)
    $connected = $async.AsyncWaitHandle.WaitOne(500)
    if (-not $connected) {
      return $false
    }

    $client.EndConnect($async)
    return $true
  } catch {
    return $false
  } finally {
    $client.Dispose()
  }
}

function Get-ListeningProcessId {
  param([int]$TargetPort)

  $line = netstat -ano -p tcp |
    Select-String ":$TargetPort" |
    Select-String "LISTENING" |
    Select-Object -First 1

  if (-not $line) {
    return $null
  }

  $match = [regex]::Match($line.ToString(), "LISTENING\s+(\d+)\s*$")
  if (-not $match.Success) {
    return $null
  }

  return [int]$match.Groups[1].Value
}

function Get-ProcessSummary {
  param([int]$ProcessId)

  try {
    $proc = Get-Process -Id $ProcessId -ErrorAction Stop
    return "$($proc.ProcessName) (PID $ProcessId)"
  } catch {
    return "PID $ProcessId"
  }
}

if (-not $env:ALLOWED_ORIGINS) {
  $env:ALLOWED_ORIGINS = "http://localhost:5173,http://localhost:5174,http://localhost:5175"
}
if (-not $env:LLAMA_API_URL) {
  $env:LLAMA_API_URL = "http://127.0.0.1:11434/api/generate"
}
if (-not $env:LLAMA_MODEL) {
  $env:LLAMA_MODEL = "mistral:latest"
}
if (-not $env:LLAMA_FALLBACK_MODEL) {
  $env:LLAMA_FALLBACK_MODEL = "llama3:8b"
}
if (-not $env:LLAMA_TIMEOUT_SECONDS) {
  $env:LLAMA_TIMEOUT_SECONDS = "45"
}
if (-not $env:DATABASE_URL) {
  $localDbPath = Join-Path $env:TEMP "ai_interview_app\app.db"
  $localDbUrlPath = $localDbPath.Replace("\", "/")
  $env:DATABASE_URL = "sqlite:///$localDbUrlPath"
}
if (-not $env:JWT_SECRET) {
  $env:JWT_SECRET = "dev-secret-change-me"
}
if (-not $env:JWT_EXPIRES_MINUTES) {
  $env:JWT_EXPIRES_MINUTES = "720"
}

$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$pythonCmd = if (Test-Path $venvPython) { $venvPython } else { "python" }

$portInUse = Test-PortOpen -TargetPort $Port
$existingPid = if ($portInUse) { Get-ListeningProcessId -TargetPort $Port } else { $null }

if ($portInUse) {
  $summary = if ($existingPid) { Get-ProcessSummary -ProcessId $existingPid } else { "another local process" }

  if ($KillExisting) {
    if (-not $existingPid) {
      Write-Host "Port $Port is already in use, but the owning process could not be identified automatically."
      Write-Host "Close the existing backend manually or use a different port, for example:"
      Write-Host "  .\run_backend.ps1 -Port 8001 -Reload"
      exit 1
    }

    Write-Host "Port $Port is already in use by $summary. Stopping it first..."
    Stop-Process -Id $existingPid -Force
    Start-Sleep -Seconds 1
  } elseif ($AllowExisting) {
    Write-Host "Backend appears to already be running on http://127.0.0.1:$Port via $summary."
    Write-Host "Reusing the existing server. Nothing else to start."
    exit 0
  } else {
    Write-Host "Port $Port is already in use by $summary."
    Write-Host ""
    Write-Host "Use one of these commands:"
    Write-Host "  .\run_backend.ps1 -AllowExisting     # if you just want to reuse the running backend"
    Write-Host "  .\run_backend.ps1 -KillExisting      # stop the old process and start a fresh one"
    Write-Host "  .\run_backend.ps1 -Port 8001         # run on a different port"
    exit 1
  }
}

$args = @("-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "$Port")
if ($Reload) {
  $args += "--reload"
}

Write-Host "Starting backend on http://127.0.0.1:$Port"
if ($Reload) {
  Write-Host "Reload mode: enabled"
}

Push-Location $projectRoot
try {
  & $pythonCmd @args
} finally {
  Pop-Location
}
