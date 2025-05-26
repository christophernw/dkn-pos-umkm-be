#!/bin/bash

# Enhanced rollback script for production seeding operations
SEED_ID=$1
DRY_RUN=0
VERBOSE=0

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        --verbose|-v)
            VERBOSE=1
            shift
            ;;
        --help|-h)
            echo "Usage: $0 <SEED_ID> [--dry-run] [--verbose]"
            echo ""
            echo "Arguments:"
            echo "  SEED_ID       Seed ID to rollback (e.g., seed_20250526123456 or 20250526123456)"
            echo ""
            echo "Options:"
            echo "  --dry-run     Show what would be rolled back without making changes"
            echo "  --verbose     Show detailed output"
            echo "  --help        Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 seed_20250526123456"
            echo "  $0 20250526123456 --dry-run"
            echo "  $0 seed_20250526123456 --verbose"
            exit 0
            ;;
        *)
            if [ -z "$SEED_ID" ]; then
                SEED_ID=$1
            else
                echo "Unknown option: $1"
                exit 1
            fi
            shift
            ;;
    esac
done

# Validate seed ID is provided
if [ -z "$SEED_ID" ]; then
    echo "❌ Error: Seed ID is required"
    echo "Usage: $0 <SEED_ID> [--dry-run] [--verbose]"
    echo "Run '$0 --help' for more information"
    exit 1
fi

# Handle ID format
if [[ $SEED_ID == seed_* ]]; then
    FULL_SEED_ID=$SEED_ID
else
    FULL_SEED_ID="seed_$SEED_ID"
    if [ $VERBOSE -eq 1 ]; then
        echo "ℹ️  Using full ID: $FULL_SEED_ID"
    fi
fi

# Check for log file
LOG_DIR="./seed_logs"
LOG_FILE="$LOG_DIR/rollback_${FULL_SEED_ID}.log"
ALT_LOG_FILE="$LOG_DIR/rollback_${SEED_ID}.log"

if [ ! -f "$LOG_FILE" ] && [ -f "$ALT_LOG_FILE" ]; then
    if [ $VERBOSE -eq 1 ]; then
        echo "ℹ️  Using alternative log file: $ALT_LOG_FILE"
    fi
    LOG_FILE=$ALT_LOG_FILE
    FULL_SEED_ID=$SEED_ID
fi

if [ ! -f "$LOG_FILE" ]; then
    echo "❌ Error: Log file not found for $SEED_ID"
    echo ""
    echo "Expected locations:"
    echo "  - $LOG_FILE"
    echo "  - $ALT_LOG_FILE"
    echo ""
    if [ -d "$LOG_DIR" ]; then
        echo "Available log files:"
        ls -la "$LOG_DIR"/rollback_*.log 2>/dev/null || echo "  No rollback log files found"
    else
        echo "Seed logs directory not found: $LOG_DIR"
    fi
    exit 1
fi

echo "✅ Found log file: $LOG_FILE"

# Check if already rolled back
if [[ "$LOG_FILE" == *.rolled_back ]]; then
    echo "⚠️  Warning: This seed operation appears to have already been rolled back"
    echo "Log file: $LOG_FILE"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Rollback cancelled"
        exit 0
    fi
fi

# Show log file info
if [ $VERBOSE -eq 1 ]; then
    echo ""
    echo "📋 Log file information:"
    echo "  File: $LOG_FILE"
    echo "  Size: $(du -h "$LOG_FILE" | cut -f1)"
    echo "  Created: $(stat -c %y "$LOG_FILE" 2>/dev/null || stat -f %Sm "$LOG_FILE" 2>/dev/null || echo "Unknown")"
    echo ""
fi

# Preview mode
if [ $DRY_RUN -eq 1 ]; then
    echo "🔍 DRY RUN - Preview of rollback operation for $FULL_SEED_ID"
    echo ""
    echo "📋 Seed operation metadata:"
    head -10 "$LOG_FILE" | grep -E "^(SEED_ID|USER_EMAIL|TOKO_ID|TIMESTAMP):"
    echo ""
    echo "📊 Summary of entities to be rolled back:"
    grep -E "^(TOTAL_|CREATED_)" "$LOG_FILE" | grep -E "(PRODUCTS|CATEGORIES|TRANSACTIONS|TRANSACTION_ITEMS)" | sort
    echo ""
    echo "To execute actual rollback, run:"
    echo "  $0 $SEED_ID"
    exit 0
fi

# Confirmation prompt for actual rollback
echo ""
echo "⚠️  WARNING: This will permanently delete seeded data!"
echo "Seed ID: $FULL_SEED_ID"
echo ""
read -p "Are you sure you want to proceed with rollback? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Rollback cancelled"
    exit 0
fi

# Execute the rollback
echo "🔄 Rolling back $FULL_SEED_ID..."
echo ""

if [ $VERBOSE -eq 1 ]; then
    python manage.py seed_database --mode=production --rollback-id="$FULL_SEED_ID"
else
    python manage.py seed_database --mode=production --rollback-id="$FULL_SEED_ID" 2>&1 | grep -E "(SUCCESS|ERROR|WARNING|✅|❌|⚠️)"
fi

ROLLBACK_EXIT_CODE=$?

if [ $ROLLBACK_EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✅ Rollback completed successfully!"
    echo "Log file has been marked as rolled back: ${LOG_FILE}.rolled_back"
else
    echo ""
    echo "❌ Rollback failed with exit code: $ROLLBACK_EXIT_CODE"
    echo "Check the output above for error details"
    exit $ROLLBACK_EXIT_CODE
fi