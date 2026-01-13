# Training Session Management

## Session Limits

- **Maximum per session**: 5 hours
- **Maximum per day**: 5 hours
- **Automatic stopping**: Training stops at time limit
- **Checkpoint saving**: Models saved automatically

## How It Works

### Session Tracking
- Tracks all training sessions
- Records daily totals
- Prevents exceeding daily limits
- Saves session history

### Automatic Checkpointing
- Saves checkpoints during training
- Can resume from last checkpoint
- Prevents loss of progress

### Time Limit Enforcement
- Monitors training time
- Stops at 5-hour session limit
- Stops at 5-hour daily limit
- Saves model before stopping

## Usage

### Start Training Session
```bash
cd mishka/training
bash scripts/run_phase1_limited.sh
```

### Check Status
```bash
python3 scripts/train_with_limits.py --status
```

Output shows:
- Today's training hours
- Remaining hours today
- Total training hours
- Total sessions

### Resume Training
Training automatically resumes from last checkpoint if interrupted.

## Daily Schedule Example

**Day 1**:
- Session 1: 5 hours (morning)
- Total: 5/5 hours ✅

**Day 2**:
- Session 1: 5 hours (morning)
- Total: 5/5 hours ✅

**Day 3**:
- Session 1: 3 hours (morning)
- Session 2: 2 hours (afternoon)
- Total: 5/5 hours ✅

## Training Progress

With 5-hour daily limit:
- **1,000 samples**: ~3-6 hours = 1-2 days
- **Full 1,912 samples**: ~6-12 hours = 2-3 days
- **Phase 1 complete**: ~1-2 weeks (with daily limits)

## Benefits

1. **System Stability**: Prevents overloading system
2. **Resource Management**: Controlled resource usage
3. **Progress Tracking**: Know exactly how much training done
4. **Resumable**: Can continue next day seamlessly
5. **Checkpoint Safety**: Never lose progress

## Session File

Sessions tracked in: `training_sessions.json`

Contains:
- Session history
- Daily totals
- Training statistics
- Resume information
