# Windows Deployment Setup Guide

This guide explains how to set up automated deployment on your Windows machine.

## 🚀 One-Command Setup

**Run this command in PowerShell as Administrator:**

```powershell
# Download and run the setup script
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/jimtin/sercureclaw/main/setup-windows-deployment.ps1" -OutFile "$env:TEMP\setup-windows-deployment.ps1"
powershell -ExecutionPolicy Bypass -File "$env:TEMP\setup-windows-deployment.ps1"
```

Or if you've already cloned the repo:

```powershell
# Navigate to your repo
cd C:\path\to\sercureclaw

# Run the setup script
powershell -ExecutionPolicy Bypass -File setup-windows-deployment.ps1
```

## What the Script Does

1. ✅ Verifies prerequisites (Docker, Git, GitHub CLI)
2. ✅ Installs missing tools automatically
3. ✅ Clones the repository to `C:\SecureClaw`
4. ✅ Creates `.env` file from template
5. ✅ Sets up GitHub Actions self-hosted runner
6. ✅ Installs runner as Windows service
7. ✅ Creates deployment scripts
8. ✅ Creates deployment workflow file

## Manual Setup Options

### Custom Deployment Path

```powershell
.\setup-windows-deployment.ps1 -DeploymentPath "D:\MyProjects\SecureClaw"
```

### Skip Runner Setup (Manual Later)

```powershell
.\setup-windows-deployment.ps1 -SkipRunnerSetup
```

### Enable Auto-Start on Boot

```powershell
.\setup-windows-deployment.ps1 -AutoStart
```

### Custom Runner Path

```powershell
.\setup-windows-deployment.ps1 -RunnerPath "D:\actions-runner"
```

## Post-Setup Steps

### 1. Configure Environment Variables

Edit your `.env` file with production credentials:

```powershell
notepad C:\SecureClaw\.env
```

Required:
- `DISCORD_TOKEN` - Your Discord bot token
- `GEMINI_API_KEY` - Your Gemini API key

Optional:
- `ANTHROPIC_API_KEY` - Claude API key
- `OPENAI_API_KEY` - OpenAI API key

### 2. Test Deployment

```powershell
cd C:\SecureClaw
.\deploy-windows.ps1
```

### 3. Commit Workflow File

```powershell
git add .github/workflows/deploy-windows.yml
git commit -m "feat: add Windows deployment workflow"
git push origin main
```

### 4. Verify Runner

Check runner status:

```powershell
cd C:\actions-runner
.\svc.sh status
```

You should see the runner online in GitHub:
`https://github.com/jimtin/sercureclaw/settings/actions/runners`

## Available Commands

After setup, these scripts are available in your deployment directory:

### Deploy Now
```powershell
.\deploy-windows.ps1
```
Pulls latest code and hot-swaps containers.

### Quick Deploy (No Build)
```powershell
.\deploy-windows.ps1 -NoBuild
```
Restarts containers without rebuilding (faster).

### Start Bot
```powershell
.\start.ps1
```
Starts the bot containers.

### Stop Bot
```powershell
.\stop.ps1
```
Stops the bot containers.

### View Logs
```powershell
.\logs.ps1
```
Shows live logs from the bot (Ctrl+C to exit).

### Auto-Deploy Monitor
```powershell
.\auto-deploy.ps1
```
Polls GitHub every 60 seconds and auto-deploys on changes.

Custom interval:
```powershell
.\auto-deploy.ps1 -IntervalSeconds 30
```

## How Automatic Deployment Works

1. **You push code to GitHub** → CI pipeline runs
2. **CI passes** → `deploy-windows.yml` workflow triggers
3. **Self-hosted runner** picks up the job (your Windows machine)
4. **Deployment runs:**
   - Pulls latest code
   - Preserves `.env` file
   - Stops old containers (30s graceful shutdown)
   - Builds new Docker image
   - Starts new containers
5. **Bot reconnects** with new code (<1 minute downtime)

## Monitoring & Management

### Check Runner Status
```powershell
cd C:\actions-runner
.\svc.sh status
```

### View Runner Logs
```powershell
cd C:\actions-runner
Get-Content -Path "_diag\Runner_*.log" -Tail 50 -Wait
```

### Restart Runner Service
```powershell
cd C:\actions-runner
.\svc.sh stop
.\svc.sh start
```

### View Container Status
```powershell
docker ps --filter "name=secureclaw"
```

### View Container Logs
```powershell
docker logs secureclaw-bot --tail 50 --follow
```

### Check Deployment History
```powershell
gh run list --workflow=deploy-windows.yml --limit 10
```

## Troubleshooting

### Runner Not Starting

```powershell
# Check service status
cd C:\actions-runner
.\svc.sh status

# View detailed logs
Get-Content -Path "_diag\Runner_*.log" -Tail 100

# Restart service
.\svc.sh stop
.\svc.sh start
```

### Docker Not Running

```powershell
# Check if Docker is running
docker info

# If not, start Docker Desktop
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

# Wait 30 seconds
Start-Sleep -Seconds 30

# Verify
docker info
```

### Deployment Failing

```powershell
# Check container logs
docker logs secureclaw-bot --tail 100

# Check Docker Compose logs
docker-compose logs

# Verify .env file exists
Test-Path C:\SecureClaw\.env

# Check Docker Compose config
docker-compose config
```

### Container Won't Start

```powershell
# Clean restart
cd C:\SecureClaw
docker-compose down -v
docker system prune -f
docker-compose build --no-cache
docker-compose up -d

# Check logs
docker logs secureclaw-bot --follow
```

### Runner Offline in GitHub

```powershell
# Remove old runner
cd C:\actions-runner
.\config.cmd remove --token YOUR_REMOVAL_TOKEN

# Get new token from GitHub
# https://github.com/jimtin/sercureclaw/settings/actions/runners/new

# Re-register
.\config.cmd --url https://github.com/jimtin/sercureclaw --token YOUR_NEW_TOKEN --name windows-production

# Reinstall service
.\svc.sh install
.\svc.sh start
```

## Uninstall

### Remove Runner

```powershell
cd C:\actions-runner
.\svc.sh stop
.\svc.sh uninstall

# Get removal token from GitHub and run:
.\config.cmd remove --token YOUR_REMOVAL_TOKEN

# Remove directory
cd \
Remove-Item -Recurse -Force C:\actions-runner
```

### Remove Deployment

```powershell
# Stop containers
cd C:\SecureClaw
docker-compose down -v

# Remove deployment
cd \
Remove-Item -Recurse -Force C:\SecureClaw
```

### Remove Auto-Start Task

```powershell
Unregister-ScheduledTask -TaskName "SecureClaw-AutoStart" -Confirm:$false
```

## Alternative: Polling Script (No Runner)

If you prefer not to set up the GitHub runner, use the polling script:

```powershell
cd C:\SecureClaw

# Run continuously in a PowerShell window
.\auto-deploy.ps1

# Or run in background with Task Scheduler
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-File C:\SecureClaw\auto-deploy.ps1"
$trigger = New-ScheduledTaskTrigger -AtStartup
Register-ScheduledTask -TaskName "SecureClaw-Monitor" -Action $action -Trigger $trigger
```

This polls GitHub every 60 seconds instead of getting instant notifications.

## Security Notes

- ✅ Runner communicates outbound only (no open ports)
- ✅ .env file never committed to Git
- ✅ Runner runs as Windows service with your user account
- ✅ GitHub Actions secrets not needed (uses local .env)
- ✅ No external webhooks or exposed endpoints

## Cost

**$0/month** - Everything runs on your local Windows machine, no cloud costs.

## Support

For issues:
1. Check [Troubleshooting](#troubleshooting) section above
2. View logs: `.\logs.ps1`
3. Open issue: https://github.com/jimtin/sercureclaw/issues

---

**Last Updated:** 2026-02-05
**Version:** 1.0.0
