#!/bin/bash
# deploy.sh — деплой SysCMS на сервер
# Вызывается после push в GitHub: git push && ./scripts/deploy.sh

set -e

SERVER="192.168.50.41"
SERVER_USER="root"
SERVER_PASS="URAL_it@"
REMOTE_DIR="/opt/syscms"

echo "=== SysCMS Deploy ==="
echo "1. Pulling latest from GitHub..."
cd "$(dirname "$0")/.."
git pull origin master

echo "2. Stopping server..."
sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER" \
    "pkill -f 'python3 app.py' 2>/dev/null; sleep 1; echo STOPPED"

echo "3. Creating backup..."
BACKUP_FILE="syscms_backup_$(date +%Y%m%d_%H%M%S).tar.gz"
sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER" \
    "cd $REMOTE_DIR && tar czf /tmp/$BACKUP_FILE app.py templates/ && cp /tmp/$BACKUP_FILE /opt/$BACKUP_FILE && echo BACKUP=$BACKUP_FILE"

echo "4. Uploading files..."
scp -r -o StrictHostKeyChecking=no \
    app.py \
    templates/ \
    static/ \
    "$SERVER_USER@$SERVER:$REMOTE_DIR/"

echo "5. Starting server..."
sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER" \
    "cd $REMOTE_DIR && nohup python3 app.py > /var/log/syscms.log 2>&1 & disown && sleep 2 && echo STARTED"

echo "=== Deploy complete ==="
