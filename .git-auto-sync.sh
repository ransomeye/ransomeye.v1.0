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

# Set up environment for cron (cron has minimal PATH)
export PATH="/usr/bin:/bin:/usr/local/bin:$PATH"
export HOME="$HOME"

# Ensure git credential helper is configured
git config credential.helper store

# Configure git for better timeout handling and large file support
git config http.postBuffer 524288000  # 500MB buffer
git config http.timeout 300  # 5 minute timeout
git config http.lowSpeedLimit 1000
git config http.lowSpeedTime 300

# Function to log messages
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

log "Starting auto-sync check..."

# Check if there are any changes (modified, staged, or untracked files)
if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
    log "No changes detected. Repository is clean."
    rm -f "$LOCK_FILE"
    exit 0
fi

log "Changes detected. Staging files..."

# Stage all changes (including new files and modifications)
# Exclude large files that exceed GitHub's limits
git add -A
# Remove any large files that might have been staged
git reset HEAD -- "*.deb" "*.rpm" "*.dmg" "*.pkg" 2>/dev/null || true

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
    
    # Retry push up to 3 times with exponential backoff
    MAX_RETRIES=3
    RETRY_COUNT=0
    PUSH_SUCCESS=false
    
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if git push origin main >> "$LOG_FILE" 2>&1; then
            log "Push successful. Auto-sync complete."
            PUSH_SUCCESS=true
            break
        else
            RETRY_COUNT=$((RETRY_COUNT + 1))
            if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
                WAIT_TIME=$((2 ** RETRY_COUNT))
                log "Push failed. Retrying in ${WAIT_TIME} seconds... (Attempt $RETRY_COUNT/$MAX_RETRIES)"
                sleep $WAIT_TIME
            else
                log "ERROR: Push failed after $MAX_RETRIES attempts. Check log for details."
            fi
        fi
    done
    
    if [ "$PUSH_SUCCESS" = false ]; then
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
