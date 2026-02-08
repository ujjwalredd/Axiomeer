#!/bin/bash

# Database restore script
set -e

PROJECT_ROOT="/Users/ujjwalreddyks/Desktop/Desktop/Ai Market Place"
BACKUP_DIR="$PROJECT_ROOT/backups"

if [ -z "$1" ]; then
    echo "Usage: $0 <backup_filename>"
    echo ""
    echo "Available backups:"
    ls -1t "$BACKUP_DIR" | head -10
    exit 1
fi

BACKUP_FILE="$1"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_FILE"

echo "======================================"
echo "Database Restore Utility"
echo "======================================"
echo ""

# Check if backup file exists
if [ ! -f "$BACKUP_PATH" ]; then
    echo "❌ ERROR: Backup file not found: $BACKUP_PATH"
    exit 1
fi

# Get database connection details
DB_CONTAINER="axiomeer_db"
DB_NAME="axiomeer"
DB_USER="axiomeer"

echo "Restore Details:"
echo "  Container: $DB_CONTAINER"
echo "  Database: $DB_NAME"
echo "  Backup file: $BACKUP_FILE"
echo "  Backup size: $(du -h "$BACKUP_PATH" | cut -f1)"
echo ""

# Confirm restore
read -p "⚠️  This will OVERWRITE the current database. Continue? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

echo ""
echo "Starting restore..."
echo ""

# Drop and recreate database
echo "1. Dropping existing database..."
docker exec $DB_CONTAINER psql -U $DB_USER -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;" > /dev/null 2>&1
echo "   ✅ Database dropped"

echo "2. Creating fresh database..."
docker exec $DB_CONTAINER psql -U $DB_USER -d postgres -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" > /dev/null 2>&1
echo "   ✅ Database created"

echo "3. Restoring from backup..."
cat "$BACKUP_PATH" | docker exec -i $DB_CONTAINER psql -U $DB_USER -d $DB_NAME > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "   ✅ Restore completed successfully!"
    echo ""

    # Verify restore
    TABLE_COUNT=$(docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c "\dt" 2>/dev/null | grep -c "public |" || echo "0")
    echo "Verification:"
    echo "  Tables restored: $TABLE_COUNT"
    echo ""

    echo "======================================"
    echo "✅ RESTORE SUCCESSFUL"
    echo "======================================"
    echo ""
    echo "Database has been restored from: $BACKUP_FILE"
    echo ""
    echo "Next steps:"
    echo "  1. Restart API container: docker-compose restart api"
    echo "  2. Verify system health: curl http://localhost:8000/health"
    echo ""
else
    echo "   ❌ ERROR: Restore failed!"
    exit 1
fi
