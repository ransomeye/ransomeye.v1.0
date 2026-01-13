# GitHub Auto-Sync Status

## Overview
Automatic file-by-file backup to GitHub is now fully configured and running.

## Active Auto-Sync Mechanisms

### 1. Real-Time File Watcher (Primary)
- **Status**: ✅ **ACTIVE**
- **Service**: `git-file-watcher.service`
- **Description**: Watches for file changes in real-time using `inotifywait` and triggers immediate sync
- **Location**: `/home/ransomeye/rebuild/.git-file-watcher.sh`
- **Log**: `/home/ransomeye/rebuild/.git-file-watcher.log`

**How it works:**
- Monitors all files in the repository for changes (modify, create, delete, move)
- Automatically commits and pushes changes within 2-5 seconds of file modification
- Excludes temporary files, logs, and git internals

**Check status:**
```bash
sudo systemctl status git-file-watcher.service
```

### 2. Periodic Sync Timer (Backup)
- **Status**: ✅ **ACTIVE**
- **Service**: `git-auto-sync.timer`
- **Description**: Runs every 15 minutes to ensure no changes are missed
- **Location**: `/home/ransomeye/rebuild/.git-auto-sync.sh`
- **Log**: `/home/ransomeye/rebuild/.git-auto-sync.log`

**How it works:**
- Checks for uncommitted changes every 15 minutes
- Commits and pushes any pending changes
- Acts as a safety net in case the file watcher misses something

**Check status:**
```bash
sudo systemctl status git-auto-sync.timer
```

### 3. Cron Job (Legacy Backup)
- **Status**: ✅ **ACTIVE**
- **Schedule**: Every 15 minutes
- **Command**: `/home/ransomeye/rebuild/.git-auto-sync.sh`

**Check status:**
```bash
crontab -l
```

## Configuration

### Git Timeout Settings
Configured to handle large files and network issues:
- HTTP Post Buffer: 500MB
- HTTP Timeout: 5 minutes
- Low Speed Limit: 1000 bytes/sec
- Low Speed Time: 5 minutes

### Retry Logic
- Automatic push retries (up to 3 attempts)
- Exponential backoff between retries
- Handles network timeouts gracefully

## GitHub Remote
- **Remote**: `origin`
- **URL**: `https://github.com/ransomeye/ransomeye.v1.0.git`
- **Branch**: `main`

## Monitoring

### View Real-Time File Watcher Logs
```bash
tail -f /home/ransomeye/rebuild/.git-file-watcher.log
```

### View Periodic Sync Logs
```bash
tail -f /home/ransomeye/rebuild/.git-auto-sync.log
```

### Check All Services Status
```bash
sudo systemctl status git-file-watcher.service git-auto-sync.timer
```

### Verify Processes Running
```bash
ps aux | grep -E "(inotifywait|git-file-watcher|git-auto-sync)"
```

## Manual Sync
If you need to manually trigger a sync:
```bash
bash /home/ransomeye/rebuild/.git-auto-sync.sh
```

## Troubleshooting

### Service Not Running
```bash
sudo systemctl start git-file-watcher.service
sudo systemctl enable git-file-watcher.service
```

### Permission Issues
```bash
sudo chown -R ransomeye:ransomeye /home/ransomeye/rebuild/.git-*
sudo chmod +x /home/ransomeye/rebuild/.git-*.sh
```

### Check for Push Failures
```bash
grep -i error /home/ransomeye/rebuild/.git-auto-sync.log
```

## Excluded Files
The following are automatically excluded from auto-sync:
- `.git/` directory
- `*.log`, `*.lock`, `*.pid` files
- `__pycache__/` directories
- `node_modules/`
- Temporary files (`.swp`, `.swo`, `.tmp`, `.bak`, `.cache`)
- Large binary files (`.deb`, `.rpm`, `.dmg`, `.pkg`)

## Last Updated
2026-01-13 19:35 IST
