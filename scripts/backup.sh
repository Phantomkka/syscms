#!/bin/bash
# backup.sh — сделать бэкап файлов с сервера
set -e
cd "$(dirname "$0")/.."
BACKUP="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP"
scp -r root@192.168.50.41:/opt/syscms/app.py "$BACKUP/"
scp -r root@192.168.50.41:/opt/syscms/templates/ "$BACKUP/"
scp -r root@192.168.50.41:/opt/syscms/static/ "$BACKUP/"
git add "$BACKUP"
git commit -m "backup: $BACKUP"
echo "Backup saved: $BACKUP"
