#!/bin/bash
# backup.sh — бэкап всего проекта с сервера на GitHub

set -e

SERVER="192.168.50.41"
SERVER_USER="root"
SERVER_PASS="URAL_it@"
REMOTE_DIR="/opt/syscms"

echo "=== SysCMS Backup ==="

echo "1. Downloading files from server..."
TMPDIR=$(mktemp -d)
scp -r -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER:$REMOTE_DIR/app.py" "$TMPDIR/" 2>/dev/null || true
scp -r -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER:$REMOTE_DIR/templates/" "$TMPDIR/" 2>/dev/null || true
scp -r -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER:$REMOTE_DIR/static/" "$TMPDIR/" 2>/dev/null || true

echo "2. Creating backup..."
BACKUP_FILE="syscms_backup_$(date +%Y%m%d_%H%M%S).tar.gz"
tar czf "$BACKUP_FILE" -C "$TMPDIR" .
echo "Backup saved: $BACKUP_FILE"

echo "3. Cleaning up..."
rm -rf "$TMPDIR"

echo "=== Backup complete ==="
echo "Commit and push to GitHub: git add $BACKUP_FILE && git commit -m 'Backup: $BACKUP_FILE' && git push"
