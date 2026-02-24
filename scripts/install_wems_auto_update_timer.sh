#!/usr/bin/env bash
set -euo pipefail

SRC_DIR="$HOME/Projects/wems-mcp-server/systemd"
DST_DIR="$HOME/.config/systemd/user"
mkdir -p "$DST_DIR"

install -m 0644 "$SRC_DIR/wems-auto-update.service" "$DST_DIR/wems-auto-update.service"
install -m 0644 "$SRC_DIR/wems-auto-update.timer" "$DST_DIR/wems-auto-update.timer"

systemctl --user daemon-reload
systemctl --user enable --now wems-auto-update.timer

echo "Installed and enabled wems-auto-update.timer"
systemctl --user status wems-auto-update.timer --no-pager | sed -n '1,20p'
