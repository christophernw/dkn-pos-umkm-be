#!/bin/bash
# rollback_seeding.sh

# This script provides a wrapper around the seed_database management command's
# rollback functionality, making it easier to use in production environments.

# Check if required arguments are provided
if [ "$#" -lt 1 ]; then
    echo "Usage: $0 SEED_ID [OPTIONS]"
    echo "Options:"
    echo "  --dry-run    Show what would be deleted without actually rolling back"
    echo "  --help       Show this help message"
    exit 1
fi

SEED_ID=$1
DRY_RUN=0

# Process additional options
shift
while [ "$#" -gt 0 ]; do
    case "$1" in
        --dry-run)
            DRY_RUN=1
            ;;
        --help)
            echo "Usage: $0 SEED_ID [OPTIONS]"
            echo "Options:"
            echo "  --dry-run    Show what would be deleted without actually rolling back"
            echo "  --help       Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help to see available options"
            exit 1
            ;;
    esac
    shift
done

# Find the path to the Django project directory (parent of the script's directory)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Check if the rollback log exists
LOG_DIR="$PROJECT_DIR/seed_logs"
LOG_FILE="$LOG_DIR/rollback_${SEED_ID}.log"

if [ ! -f "$LOG_FILE" ]; then
    echo "Error: Rollback log not found for seed ID: $SEED_ID"
    echo "Check if the ID is correct and the log file exists at: $LOG_FILE"
    exit 1
fi

# If dry run, just show information about what would be rolled back
if [ "$DRY_RUN" -eq 1 ]; then
    echo "DRY RUN - No changes will be made"
    echo "The following seed operation would be rolled back:"
    echo "Seed ID: $SEED_ID"
    
    # Extract and display information from the log file
    USER_EMAIL=$(grep "USER_EMAIL" "$LOG_FILE" | cut -d ' ' -f 2)
    TOKO_ID=$(grep "TOKO_ID" "$LOG_FILE" | cut -d ' ' -f 2)
    TIMESTAMP=$(grep "TIMESTAMP" "$LOG_FILE" | cut -d ' ' -f 2)
    
    echo "User Email: $USER_EMAIL"
    echo "Toko ID: $TOKO_ID"
    echo "Timestamp: $TIMESTAMP"
    
    # Count what would be deleted
    PRODUCTS_BEFORE=$(grep "BEFORE_PRODUCTS" "$LOG_FILE" | cut -d ' ' -f 2)
    PRODUCTS_AFTER=$(grep "AFTER_PRODUCTS" "$LOG_FILE" | cut -d ' ' -f 2)
    PRODUCTS_ADDED=$((PRODUCTS_AFTER - PRODUCTS_BEFORE))
    
    CATEGORIES_BEFORE=$(grep "BEFORE_CATEGORIES" "$LOG_FILE" | cut -d ' ' -f 2)
    CATEGORIES_AFTER=$(grep "AFTER_CATEGORIES" "$LOG_FILE" | cut -d ' ' -f 2)
    CATEGORIES_ADDED=$((CATEGORIES_AFTER - CATEGORIES_BEFORE))
    
    TRANSACTIONS_BEFORE=$(grep "BEFORE_TRANSACTIONS" "$LOG_FILE" | cut -d ' ' -f 2)
    TRANSACTIONS_AFTER=$(grep "AFTER_TRANSACTIONS" "$LOG_FILE" | cut -d ' ' -f 2)
    TRANSACTIONS_ADDED=$((TRANSACTIONS_AFTER - TRANSACTIONS_BEFORE))
    
    echo "Would delete:"
    echo "  - $PRODUCTS_ADDED products"
    echo "  - $CATEGORIES_ADDED categories"
    echo "  - $TRANSACTIONS_ADDED transactions"
    
    echo "To perform the actual rollback, run this command without --dry-run"
    exit 0
fi

# Confirm before proceeding
echo "WARNING: You are about to roll back seed operation: $SEED_ID"
echo "This will delete all data created during that seeding operation."
echo "This action cannot be undone."
echo ""
echo "Do you want to proceed? (y/n)"
read -r CONFIRM

if [ "$CONFIRM" != "y" ]; then
    echo "Rollback cancelled."
    exit 0
fi

# Run the management command to perform the rollback
cd "$PROJECT_DIR"

# Check if we're in a Docker environment
if [ -f /.dockerenv ] || [ -f /run/.containerenv ]; then
    # Running inside Docker
    python manage.py seed_database --mode=production --rollback-id="$SEED_ID"
else
    # Check if docker-compose is available and if the Django container is running
    if command -v docker-compose &> /dev/null; then
        # We're on the host system - try to run through docker-compose
        COMPOSE_FILE=""
        if [ -f docker-compose.yml ]; then
            COMPOSE_FILE="docker-compose.yml"
        elif [ -f docker-compose.yaml ]; then
            COMPOSE_FILE="docker-compose.yaml"
        fi
        
        if [ -n "$COMPOSE_FILE" ]; then
            echo "Running rollback through docker-compose..."
            docker-compose -f "$COMPOSE_FILE" exec web python manage.py seed_database --mode=production --rollback-id="$SEED_ID"
        else
            echo "Error: No docker-compose.yml file found, and not running inside Docker."
            echo "Please run this script inside the Docker container or where docker-compose.yml is available."
            exit 1
        fi
    else
        # No Docker, try to run locally
        echo "Running rollback directly..."
        # Check if Python/Django is available
        if command -v python &> /dev/null; then
            python manage.py seed_database --mode=production --rollback-id="$SEED_ID"
        else
            echo "Error: Cannot run the rollback command."
            echo "Please ensure you're either in the Docker container, have docker-compose"
            echo "available, or have Python and Django installed locally."
            exit 1
        fi
    fi
fi

echo "Rollback completed."