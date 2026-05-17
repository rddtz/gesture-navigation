#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
MATCH="$DIR/.venv/bin/python"

if pgrep -f "$MATCH" > /dev/null 2>&1; then
    pkill -f "$MATCH"
    notify-send "Gesture Control" "Stopped" 2>/dev/null || true
else
    cd "$DIR" && uv run python main.py "$@" &>/dev/null &
    notify-send "Gesture Control" "Started" 2>/dev/null || true
fi
