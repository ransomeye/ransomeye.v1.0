# Daily Training Guide - 5 Hours/Day Limit

## Training Constraints

- **Maximum per session**: 5 hours
- **Maximum per day**: 5 hours
- **Automatic stopping**: Training stops at limits
- **Checkpoint saving**: Progress saved automatically

## Daily Workflow

### Morning Session (Recommended)
```bash
cd mishka/training
source venv/bin/activate
bash scripts/run_phase1_limited.sh
```

This will:
1. Check if you can start (daily limit check)
2. Start 5-hour session (or remaining hours if less)
3. Automatically stop at time limit
4. Save checkpoint

### Check Status Anytime
```bash
python3 scripts/train_with_limits.py --status
```

Shows:
- Today's training hours
- Remaining hours today
- Total training hours
- Session count

### Resume Next Day
```bash
bash scripts/resume_training.sh
```

Automatically resumes from last checkpoint.

## Example Daily Schedule

### Day 1
```bash
# Morning: 5-hour session
bash scripts/run_phase1_limited.sh
# Status: 5.0/5.0 hours ✅
```

### Day 2
```bash
# Morning: 5-hour session  
bash scripts/run_phase1_limited.sh
# Status: 5.0/5.0 hours ✅
```

### Day 3
```bash
# Morning: 3-hour session
bash scripts/run_phase1_limited.sh
# Status: 3.0/5.0 hours

# Afternoon: 2-hour session
bash scripts/run_phase1_limited.sh
# Status: 5.0/5.0 hours ✅
```

## Training Progress Tracking

### Current Training
- **1,000 samples**: ~3-6 hours = 1-2 days
- **Full 1,912 samples**: ~6-12 hours = 2-3 days
- **Phase 1 complete**: ~1-2 weeks (with daily limits)

### Phase Completion Estimates

| Phase | Estimated Hours | Days (5hr/day) |
|-------|----------------|----------------|
| Phase 1: Cybersecurity | 20-30 hours | 4-6 days |
| Phase 2: RansomEye | 20-30 hours | 4-6 days |
| Phase 3: Conversational | 20-30 hours | 4-6 days |
| Phase 4: RAG Optimization | 15-20 hours | 3-4 days |

## Benefits

1. **System Stability**: Never overloads system
2. **Controlled Resources**: Stays within 50% allocation
3. **Progress Tracking**: Know exactly what's done
4. **Resumable**: Continue seamlessly next day
5. **Safe**: Checkpoints prevent progress loss

## Session File

All sessions tracked in: `training_sessions.json`

View with:
```bash
cat training_sessions.json | python3 -m json.tool
```

## Tips

1. **Start early**: Use full 5 hours in morning
2. **Check status**: Before starting, check remaining hours
3. **Let it run**: Training is slow, be patient
4. **Resume next day**: Training continues from checkpoint
5. **Monitor progress**: Check logs in `models/phase1/`

## Commands Summary

```bash
# Start training (with limits)
bash scripts/run_phase1_limited.sh

# Check status
python3 scripts/train_with_limits.py --status

# Resume from checkpoint
bash scripts/resume_training.sh
```
