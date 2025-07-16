#!/usr/bin/env bash
# exit on error
set -o errexit

# Apply database migrations
python -m flask db upgrade

# Start the application
gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 