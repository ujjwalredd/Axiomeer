#!/bin/bash

# Database backup script
set -e

PROJECT_ROOT="/Users/ujjwalreddyks/Desktop/Desktop/Ai Market Place"
BACKUP_DIR="$PROJECT_ROOT/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="axiomeer_backup_$TIMESTAMP.sql"

echo "======================================"
echo "Database Backup Utility"
echo "======================================"
echo ""

# Create backups directory if it doesn't exist
if [ ! -d "$BACKUP_DIR" ]; then
    mkdir -p "$BACKUP_DIR"
    echo "✅ Created backups directory: $BACKUP_DIR"
fi
echo ""

# Get database connection details
DB_CONTAINER="axiomeer_db"
DB_NAME="axiomeer"
DB_USER="axiomeer"

echo "Backup Details:"
echo "  Container: $DB_CONTAINER"
echo "  Database: $DB_NAME"
echo "  Backup file: $BACKUP_FILE"
echo "  Location: $BACKUP_DIR"
echo ""

# Check if container is running
if ! docker ps | grep -q "$DB_CONTAINER"; then
    echo "❌ ERROR: Database container '$DB_CONTAINER' is not running"
    exit 1
fi

echo "Starting backup..."
echo ""

# Perform backup using docker exec and pg_dump
docker exec $DB_CONTAINER pg_dump -U $DB_USER -d $DB_NAME > "$BACKUP_DIR/$BACKUP_FILE"

if [ $? -eq 0 ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_DIR/$BACKUP_FILE" | cut -f1)
    echo "✅ Backup completed successfully!"
    echo ""
    echo "Backup Information:"
    echo "  File: $BACKUP_FILE"
    echo "  Size: $BACKUP_SIZE"
    echo "  Path: $BACKUP_DIR/$BACKUP_FILE"
    echo ""

    # Count tables in backup
    TABLE_COUNT=$(grep -c "CREATE TABLE" "$BACKUP_DIR/$BACKUP_FILE" || echo "0")
    echo "  Tables backed up: $TABLE_COUNT"

    # Show recent backups
    echo ""
    echo "Recent backups:"
    ls -lht "$BACKUP_DIR" | head -6
    echo ""

    echo "======================================"
    echo "✅ BACKUP SUCCESSFUL"
    echo "======================================"
    echo ""
    echo "To restore this backup:"
    echo "  ./scripts/restore_database.sh $BACKUP_FILE"
    echo ""
else
    echo "❌ ERROR: Backup failed!"
    exit 1
fi
