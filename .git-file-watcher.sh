#!/bin/bash
# Real-time file watcher for immediate GitHub sync
# Watches for file changes and triggers auto-sync immediately

REPO_DIR="/home/ransomeye/rebuild"
SYNC_SCRIPT="$REPO_DIR/.git-auto-sync.sh"
LOG_FILE="$REPO_DIR/.git-file-watcher.log"
PID_FILE="$REPO_DIR/.git-file-watcher.pid"

# Ensure log file exists and is writable
touch "$LOG_FILE" 2>/dev/null || true
chmod 666 "$LOG_FILE" 2>/dev/null || true

# Function to log messages
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE" 2>&1 || true
}

# Function to trigger sync with debouncing (wait for file to settle)
trigger_sync() {
    local file="$1"
    log "File change detected: $file"
    
    # Wait 2 seconds for file to settle (in case of rapid edits)
    sleep 2
    
    # Check if file is still being modified
    if command -v lsof > /dev/null 2>&1 && lsof "$file" > /dev/null 2>&1; then
        log "File still open, waiting..."
        sleep 3
    fi
    
    # Trigger sync
    log "Triggering auto-sync for: $file"
    bash "$SYNC_SCRIPT" &
}

cd "$REPO_DIR" || exit 1

log "Starting file watcher for real-time GitHub sync..."

# Keep the watcher running in a loop
while true; do
    # Watch for file changes (modify, create, delete, move)
    # Use --format to get consistent output
    inotifywait -m -r -e modify,create,delete,move \
        --format '%w%f %e' \
        --exclude '\.(git|log|lock|pid|swp|swo|tmp|bak|cache)$|__pycache__|\.pyc$|node_modules|\.git/' \
        "$REPO_DIR" 2>> "$LOG_FILE" | while IFS=' ' read -r full_path events; do
        # Skip if it's a git internal file or log file
        if [[ "$full_path" =~ \.git ]] || \
           [[ "$full_path" =~ \.(log|lock|pid|swp|swo|tmp|bak|cache)$ ]] || \
           [[ "$full_path" == *".git-auto-sync.log" ]] || \
           [[ "$full_path" == *".git-file-watcher.log" ]] || \
           [[ "$full_path" == *"__pycache__"* ]] || \
           [[ "$full_path" == *"node_modules"* ]]; then
            continue
        fi
        
        # Only sync actual files, not directories
        if [ -f "$full_path" ]; then
            trigger_sync "$full_path"
        fi
    done
    
    # If inotifywait exits, log and restart after a short delay
    log "inotifywait exited, restarting in 5 seconds..."
    sleep 5
done
