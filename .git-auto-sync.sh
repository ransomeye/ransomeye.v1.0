#!/bin/bash
# Auto-commit and auto-sync script for ransomeye.v1.0 repository
# This script checks for changes, commits them, and pushes to GitHub

REPO_DIR="/home/ransomeye/rebuild"
LOG_FILE="$REPO_DIR/.git-auto-sync.log"
LOCK_FILE="$REPO_DIR/.git-auto-sync.lock"

# Prevent multiple instances from running simultaneously
if [ -f "$LOCK_FILE" ]; then
    PID=$(cat "$LOCK_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Auto-sync already running (PID: $PID)" >> "$LOG_FILE"
        exit 0
    else
        rm -f "$LOCK_FILE"
    fi
fi

echo $$ > "$LOCK_FILE"
cd "$REPO_DIR" || exit 1

# Function to log messages
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

log "Starting auto-sync check..."

# Check if there are any changes
if git diff --quiet && git diff --cached --quiet; then
    log "No changes detected. Repository is clean."
    rm -f "$LOCK_FILE"
    exit 0
fi

log "Changes detected. Staging files..."

# Stage all changes (including new files and modifications)
git add -A

# Check if there are staged changes
if git diff --cached --quiet; then
    log "No changes to commit after staging."
    rm -f "$LOCK_FILE"
    exit 0
fi

# Create commit with timestamp
COMMIT_MSG="Auto-sync: $(date '+%Y-%m-%d %H:%M:%S')"
log "Committing changes: $COMMIT_MSG"

if git commit -m "$COMMIT_MSG" >> "$LOG_FILE" 2>&1; then
    log "Commit successful. Pushing to GitHub..."
    
    if git push origin main >> "$LOG_FILE" 2>&1; then
        log "Push successful. Auto-sync complete."
    else
        log "ERROR: Push failed. Check log for details."
        rm -f "$LOCK_FILE"
        exit 1
    fi
else
    log "ERROR: Commit failed. Check log for details."
    rm -f "$LOCK_FILE"
    exit 1
fi

rm -f "$LOCK_FILE"
log "Auto-sync finished successfully."
