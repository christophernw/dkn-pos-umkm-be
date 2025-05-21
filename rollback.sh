#!/bin/bash

# Simple rollback script for testing
SEED_ID=$1
DRY_RUN=0

if [ "$2" == "--dry-run" ]; then
    DRY_RUN=1
fi

# Handle ID format
if [[ $SEED_ID == seed_* ]]; then
    FULL_SEED_ID=$SEED_ID
else
    FULL_SEED_ID="seed_$SEED_ID"
    echo "Using ID: $FULL_SEED_ID"
fi

# Check for log file
LOG_DIR="./seed_logs"
LOG_FILE="$LOG_DIR/rollback_${FULL_SEED_ID}.log"
ALT_LOG_FILE="$LOG_DIR/rollback_${SEED_ID}.log"

if [ ! -f "$LOG_FILE" ] && [ -f "$ALT_LOG_FILE" ]; then
    echo "Using alternative log file: $ALT_LOG_FILE"
    LOG_FILE=$ALT_LOG_FILE
    FULL_SEED_ID=$SEED_ID
fi

if [ ! -f "$LOG_FILE" ]; then
    echo "Error: Log file not found for $SEED_ID"
    exit 1
fi

echo "Found log file: $LOG_FILE"

# If dry run, just show what would be rolled back
if [ $DRY_RUN -eq 1 ]; then
    echo "DRY RUN - would roll back $FULL_SEED_ID"
    exit 0
fi

# Execute the rollback
echo "Rolling back $FULL_SEED_ID..."
python manage.py seed_database --mode=production --rollback-id="$FULL_SEED_ID"
echo "Rollback completed."
