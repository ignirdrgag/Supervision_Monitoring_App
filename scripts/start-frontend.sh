#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../frontend"

npm install
VITE_API_BASE="${VITE_API_BASE:-http://192.168.1.116:8000/api}" npm run dev -- --host 0.0.0.0
