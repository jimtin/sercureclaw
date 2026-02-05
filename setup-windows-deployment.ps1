# SecureClaw Windows Deployment Setup Script
# This script automates the entire setup process for Windows deployment
# Run as Administrator: powershell -ExecutionPolicy Bypass -File setup-windows-deployment.ps1

#Requires -RunAsAdministrator

param(
    [string]$DeploymentPath = "C:\SecureClaw",
    [string]$RunnerPath = "C:\actions-runner",
    [switch]$SkipRunnerSetup = $false,
    [switch]$AutoStart = $false
)

$ErrorActionPreference = "Stop"

# Colors for output
function Write-ColorOutput {
    param($ForegroundColor)
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

function Write-Step {
    param([string]$message)
    Write-ColorOutput Cyan "🔧 $message"
}

function Write-Success {
    param([string]$message)
    Write-ColorOutput Green "✅ $message"
}

function Write-WarningMessage {
    param([string]$message)
    Write-ColorOutput Yellow "⚠️  $message"
}

function Write-ErrorMessage {
    param([string]$message)
    Write-ColorOutput Red "❌ $message"
}

Write-ColorOutput Cyan @"
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     SecureClaw Windows Deployment Setup                     ║
║     Automated Installation & Configuration                   ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"@

Write-Output ""
Write-Output "This script will:"
Write-Output "  1. Verify prerequisites (Docker, Git, GitHub CLI)"
Write-Output "  2. Clone the SecureClaw repository"
Write-Output "  3. Set up environment configuration"
Write-Output "  4. Install GitHub Actions self-hosted runner"
Write-Output "  5. Create deployment scripts"
Write-Output "  6. Configure auto-deployment workflow"
Write-Output ""
Write-Output "Deployment path: $DeploymentPath"
Write-Output "Runner path: $RunnerPath"
Write-Output ""

$confirmation = Read-Host "Continue with setup? (yes/no)"
if ($confirmation -ne "yes") {
    Write-WarningMessage "Setup cancelled by user"
    exit 0
}

Write-Output ""
Write-Step "Step 1: Checking prerequisites..."

# Check Docker
try {
    $dockerVersion = docker --version 2>$null
    if ($dockerVersion) {
        Write-Success "Docker installed: $dockerVersion"
    } else {
        throw "Docker not found"
    }

    # Check if Docker is running
    docker info 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Docker is running"
    } else {
        Write-WarningMessage "Docker is installed but not running. Starting Docker Desktop..."
        Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
        Write-Output "Waiting 30 seconds for Docker to start..."
        Start-Sleep -Seconds 30

        docker info 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Docker started successfully"
        } else {
            Write-ErrorMessage "Docker failed to start. Please start Docker Desktop manually and run this script again."
            exit 1
        }
    }
} catch {
    Write-ErrorMessage "Docker is not installed. Please install Docker Desktop:"
    Write-Output "  Download from: https://www.docker.com/products/docker-desktop/"
    exit 1
}

# Check Git
try {
    $gitVersion = git --version 2>$null
    if ($gitVersion) {
        Write-Success "Git installed: $gitVersion"
    } else {
        throw "Git not found"
    }
} catch {
    Write-ErrorMessage "Git is not installed. Please install Git for Windows:"
    Write-Output "  Download from: https://git-scm.com/download/win"
    Write-Output "  Or run: winget install Git.Git"
    exit 1
}

# Check GitHub CLI
try {
    $ghVersion = gh --version 2>$null
    if ($ghVersion) {
        Write-Success "GitHub CLI installed: $($ghVersion[0])"
    } else {
        throw "GitHub CLI not found"
    }
} catch {
    Write-WarningMessage "GitHub CLI is not installed. Installing now..."
    try {
        winget install GitHub.cli -e --accept-source-agreements --accept-package-agreements
        Write-Success "GitHub CLI installed"
    } catch {
        Write-ErrorMessage "Failed to install GitHub CLI. Please install manually:"
        Write-Output "  Run: winget install GitHub.cli"
        exit 1
    }
}

Write-Output ""
Write-Step "Step 2: Cloning repository..."

# Create deployment directory
if (Test-Path $DeploymentPath) {
    Write-WarningMessage "Deployment directory already exists: $DeploymentPath"
    $overwrite = Read-Host "Do you want to remove it and start fresh? (yes/no)"
    if ($overwrite -eq "yes") {
        Remove-Item -Recurse -Force $DeploymentPath
        Write-Success "Removed existing directory"
    } else {
        Write-Output "Using existing directory"
    }
} else {
    New-Item -ItemType Directory -Path $DeploymentPath -Force | Out-Null
    Write-Success "Created deployment directory: $DeploymentPath"
}

# Clone repository
Set-Location $DeploymentPath
if (Test-Path ".git") {
    Write-Output "Repository already cloned. Pulling latest changes..."
    git pull origin main
} else {
    Write-Output "Cloning repository..."
    git clone https://github.com/jimtin/sercureclaw.git .
}
Write-Success "Repository ready"

Write-Output ""
Write-Step "Step 3: Setting up environment configuration..."

# Create .env file
if (Test-Path ".env") {
    Write-WarningMessage ".env file already exists"
    $editEnv = Read-Host "Do you want to edit it? (yes/no)"
    if ($editEnv -eq "yes") {
        notepad .env
    }
} else {
    Write-Output "Creating .env file from template..."
    Copy-Item .env.example .env
    Write-Success ".env file created"
    Write-Output ""
    Write-Output "IMPORTANT: You need to edit the .env file with your credentials:"
    Write-Output "  - DISCORD_TOKEN"
    Write-Output "  - GEMINI_API_KEY"
    Write-Output "  - ANTHROPIC_API_KEY (optional)"
    Write-Output "  - OPENAI_API_KEY (optional)"
    Write-Output ""
    $editNow = Read-Host "Open .env file now to edit? (yes/no)"
    if ($editNow -eq "yes") {
        notepad .env
        Read-Host "Press Enter when you're done editing..."
    }
}

Write-Output ""
Write-Step "Step 4: Creating deployment scripts..."

# Create deploy-windows.ps1
$deployScript = @'
# deploy-windows.ps1 - SecureClaw deployment script for Windows
param(
    [switch]$SkipBackup = $false,
    [switch]$NoBuild = $false
)

Write-Host "🚀 SecureClaw Deployment" -ForegroundColor Cyan
Write-Host "========================" -ForegroundColor Cyan

# Check if Docker is running
try {
    docker info | Out-Null
} catch {
    Write-Host "❌ Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}

# Backup .env
if (-not $SkipBackup -and (Test-Path .env)) {
    Copy-Item .env .env.backup
    Write-Host "✅ Backed up .env file" -ForegroundColor Green
}

# Pull latest code
Write-Host "📥 Pulling latest code..." -ForegroundColor Yellow
git fetch origin main
$currentCommit = git rev-parse HEAD
git reset --hard origin/main
$newCommit = git rev-parse HEAD

if ($currentCommit -ne $newCommit) {
    Write-Host "✅ Updated from $($currentCommit.Substring(0,7)) to $($newCommit.Substring(0,7))" -ForegroundColor Green
} else {
    Write-Host "✅ Already up to date ($($currentCommit.Substring(0,7)))" -ForegroundColor Green
}

# Restore .env
if (Test-Path .env.backup) {
    Copy-Item .env.backup .env -Force
    Remove-Item .env.backup
    Write-Host "✅ Restored .env file" -ForegroundColor Green
}

# Hot-swap
Write-Host "🔄 Hot-swapping containers..." -ForegroundColor Yellow
docker-compose down --timeout 30

if (-not $NoBuild) {
    Write-Host "🔨 Building image..." -ForegroundColor Yellow
    docker-compose build --no-cache
}

docker-compose up -d

# Wait and verify
Write-Host "⏳ Waiting for services..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

$containers = docker ps --filter "name=secureclaw" --format "{{.Names}}"
if ($containers) {
    Write-Host "✅ Deployment successful!" -ForegroundColor Green
    Write-Host "Running containers:" -ForegroundColor Green
    docker ps --filter "name=secureclaw" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

    Write-Host "`n📋 Recent logs:" -ForegroundColor Cyan
    docker logs secureclaw-bot --tail 20
} else {
    Write-Host "❌ Deployment failed - containers not running" -ForegroundColor Red
    Write-Host "`n📋 Docker Compose logs:" -ForegroundColor Yellow
    docker-compose logs --tail 50
    exit 1
}
'@

Set-Content -Path "deploy-windows.ps1" -Value $deployScript
Write-Success "Created deploy-windows.ps1"

# Create auto-deploy polling script
$autoDeployScript = @'
# auto-deploy.ps1 - Automatic deployment polling script
param(
    [int]$IntervalSeconds = 60
)

$repoPath = Get-Location

Write-Host "🔄 SecureClaw Auto-Deployment Monitor" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Checking for updates every $IntervalSeconds seconds" -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

while ($true) {
    try {
        Set-Location $repoPath
        git fetch origin main 2>$null

        $local = git rev-parse HEAD
        $remote = git rev-parse origin/main

        if ($local -ne $remote) {
            Write-Host "🔔 New version detected!" -ForegroundColor Yellow
            Write-Host "  Local:  $($local.Substring(0,7))" -ForegroundColor Gray
            Write-Host "  Remote: $($remote.Substring(0,7))" -ForegroundColor Gray
            Write-Host "Starting deployment..." -ForegroundColor Yellow
            .\deploy-windows.ps1
            Write-Host ""
        } else {
            $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
            Write-Host "[$timestamp] ✅ Up to date ($($local.Substring(0,7)))" -ForegroundColor Green
        }
    } catch {
        Write-Host "❌ Error: $_" -ForegroundColor Red
    }

    Start-Sleep -Seconds $IntervalSeconds
}
'@

Set-Content -Path "auto-deploy.ps1" -Value $autoDeployScript
Write-Success "Created auto-deploy.ps1"

# Create quick start/stop scripts
$startScript = @'
docker-compose up -d
Write-Host "✅ SecureClaw started" -ForegroundColor Green
docker ps --filter "name=secureclaw" --format "table {{.Names}}\t{{.Status}}"
'@

$stopScript = @'
docker-compose down --timeout 30
Write-Host "✅ SecureClaw stopped" -ForegroundColor Green
'@

$logsScript = @'
docker logs secureclaw-bot --follow
'@

Set-Content -Path "start.ps1" -Value $startScript
Set-Content -Path "stop.ps1" -Value $stopScript
Set-Content -Path "logs.ps1" -Value $logsScript

Write-Success "Created helper scripts: start.ps1, stop.ps1, logs.ps1"

if (-not $SkipRunnerSetup) {
    Write-Output ""
    Write-Step "Step 5: Setting up GitHub Actions self-hosted runner..."

    Write-Output ""
    Write-Output "To complete the runner setup, you need a registration token from GitHub."
    Write-Output "I'll help you get it:"
    Write-Output ""
    Write-Output "1. Opening GitHub repository settings..."

    Start-Process "https://github.com/jimtin/sercureclaw/settings/actions/runners/new?arch=x64&os=win"

    Write-Output ""
    Write-Output "2. On the GitHub page that just opened:"
    Write-Output "   - Select: Windows (x64)"
    Write-Output "   - Copy the TOKEN from the Configure command (it starts with 'A')"
    Write-Output ""

    $token = Read-Host "Paste the registration token here"

    if ([string]::IsNullOrWhiteSpace($token)) {
        Write-WarningMessage "No token provided. Skipping runner setup."
        Write-Output "You can set up the runner manually later by running:"
        Write-Output "  powershell -File setup-runner.ps1"
    } else {
        # Create runner directory
        if (Test-Path $RunnerPath) {
            Write-WarningMessage "Runner directory already exists: $RunnerPath"
            $removeRunner = Read-Host "Remove and reinstall? (yes/no)"
            if ($removeRunner -eq "yes") {
                Remove-Item -Recurse -Force $RunnerPath
            } else {
                Write-Output "Using existing runner directory"
            }
        }

        if (-not (Test-Path $RunnerPath)) {
            New-Item -ItemType Directory -Path $RunnerPath -Force | Out-Null
        }

        Set-Location $RunnerPath

        # Download runner
        Write-Output "Downloading GitHub Actions runner..."
        $runnerVersion = "2.311.0"
        $runnerUrl = "https://github.com/actions/runner/releases/download/v$runnerVersion/actions-runner-win-x64-$runnerVersion.zip"
        $runnerZip = "actions-runner.zip"

        Invoke-WebRequest -Uri $runnerUrl -OutFile $runnerZip
        Write-Success "Downloaded runner"

        # Extract runner
        Write-Output "Extracting runner..."
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        [System.IO.Compression.ZipFile]::ExtractToDirectory("$RunnerPath\$runnerZip", $RunnerPath)
        Remove-Item $runnerZip
        Write-Success "Extracted runner"

        # Configure runner
        Write-Output "Configuring runner..."
        $configCmd = ".\config.cmd --url https://github.com/jimtin/sercureclaw --token $token --name windows-production --work _work --runasservice"
        Invoke-Expression $configCmd

        if ($LASTEXITCODE -eq 0) {
            Write-Success "Runner configured"

            # Install as service
            Write-Output "Installing runner as Windows service..."
            .\svc.sh install

            # Start service
            Write-Output "Starting runner service..."
            .\svc.sh start

            Write-Success "Runner service started"

            # Return to deployment directory
            Set-Location $DeploymentPath
        } else {
            Write-ErrorMessage "Failed to configure runner. Please set up manually."
        }
    }
} else {
    Write-WarningMessage "Skipped runner setup (--SkipRunnerSetup flag)"
}

Write-Output ""
Write-Step "Step 6: Creating deployment workflow..."

# Create .github/workflows directory if it doesn't exist
$workflowDir = ".github\workflows"
if (-not (Test-Path $workflowDir)) {
    New-Item -ItemType Directory -Path $workflowDir -Force | Out-Null
}

# Create deployment workflow
$deployWorkflow = @'
name: Deploy to Windows

on:
  workflow_run:
    workflows: ["CI/CD Pipeline"]
    types:
      - completed
    branches:
      - main

jobs:
  deploy:
    name: Deploy to Windows Production
    runs-on: self-hosted
    if: ${{ github.event.workflow_run.conclusion == 'success' }}

    steps:
      - name: Checkout latest code
        uses: actions/checkout@v4
        with:
          clean: false

      - name: Preserve .env file
        shell: powershell
        run: |
          if (Test-Path .env) {
            Copy-Item .env .env.backup
            Write-Host "✅ Backed up .env file"
          }

      - name: Pull latest changes
        shell: powershell
        run: |
          git fetch origin main
          git reset --hard origin/main
          Write-Host "✅ Pulled latest code"

      - name: Restore .env file
        shell: powershell
        run: |
          if (Test-Path .env.backup) {
            Copy-Item .env.backup .env -Force
            Remove-Item .env.backup
            Write-Host "✅ Restored .env file"
          }

      - name: Hot-swap containers
        shell: powershell
        run: |
          Write-Host "🔄 Starting hot-swap deployment..."
          docker-compose down --timeout 30
          docker-compose build
          docker-compose up -d
          Write-Host "✅ Deployment complete!"

      - name: Verify deployment
        shell: powershell
        run: |
          Write-Host "⏳ Waiting for services..."
          Start-Sleep -Seconds 15

          $running = docker ps --filter "name=secureclaw" --format "{{.Names}}"
          if ($running) {
            Write-Host "✅ Containers running: $running"
            docker logs secureclaw-bot --tail 20
          } else {
            Write-Host "❌ Deployment failed"
            exit 1
          }
'@

Set-Content -Path "$workflowDir\deploy-windows.yml" -Value $deployWorkflow
Write-Success "Created deployment workflow: .github/workflows/deploy-windows.yml"

Write-Output ""
Write-Output "⚠️  IMPORTANT: You need to commit and push this workflow file:"
Write-Output "  git add .github/workflows/deploy-windows.yml"
Write-Output "  git commit -m 'feat: add Windows deployment workflow'"
Write-Output "  git push origin main"
Write-Output ""

if ($AutoStart) {
    Write-Output ""
    Write-Step "Step 7: Setting up auto-start on boot..."

    $autoStartScript = "$DeploymentPath\deploy-windows.ps1"
    $taskAction = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -File `"$autoStartScript`" -SkipBackup"
    $taskTrigger = New-ScheduledTaskTrigger -AtStartup
    $taskPrincipal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Highest
    $taskSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

    try {
        Register-ScheduledTask -TaskName "SecureClaw-AutoStart" -Action $taskAction -Trigger $taskTrigger -Principal $taskPrincipal -Settings $taskSettings -Force | Out-Null
        Write-Success "Created auto-start scheduled task"
    } catch {
        Write-WarningMessage "Failed to create auto-start task: $_"
    }
}

Write-Output ""
Write-ColorOutput Green @"
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║                  ✅ SETUP COMPLETE!                          ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"@

Write-Output ""
Write-Output "📁 Deployment directory: $DeploymentPath"
if (-not $SkipRunnerSetup) {
    Write-Output "🏃 Runner directory: $RunnerPath"
}
Write-Output ""
Write-Output "🚀 Quick Commands:"
Write-Output "  Deploy now:           .\deploy-windows.ps1"
Write-Output "  Start bot:            .\start.ps1"
Write-Output "  Stop bot:             .\stop.ps1"
Write-Output "  View logs:            .\logs.ps1"
Write-Output "  Auto-deploy monitor:  .\auto-deploy.ps1"
Write-Output ""
Write-Output "📋 Next Steps:"
Write-Output "  1. Test deployment:   .\deploy-windows.ps1"
Write-Output "  2. Verify bot works:  .\logs.ps1"
Write-Output "  3. Commit workflow:   git add .github/workflows/deploy-windows.yml"
Write-Output "                        git commit -m 'feat: add Windows deployment workflow'"
Write-Output "                        git push origin main"
Write-Output ""
Write-Output "🔄 Automatic Deployment:"
Write-Output "  - Triggers when CI passes on main branch"
Write-Output "  - Runner service runs in background"
Write-Output "  - Check status: Set-Location $RunnerPath; .\svc.sh status"
Write-Output ""
Write-Success "Setup complete! Your Windows deployment is ready."
