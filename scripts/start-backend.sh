#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../backend"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

. .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py loaddata demo
python manage.py runserver 0.0.0.0:8000
