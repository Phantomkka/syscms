#!/bin/bash
# deploy.sh — загрузить свежее с GitHub на сервер
set -e
cd "$(dirname "$0")/.."
git pull
scp -r app.py templates/ static/ root@192.168.50.41:/opt/syscms/
sshpass -p 'URAL_it@' ssh root@192.168.50.41 'cd /opt/syscms && nohup python3 app.py > /var/log/syscms.log 2>&1 & disown'
echo "Deploy done"
