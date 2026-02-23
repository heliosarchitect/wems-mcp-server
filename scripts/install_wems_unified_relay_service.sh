#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="wems-unified-relay.service"
SRC="/home/bonsaihorn/Projects/wems-mcp-server/systemd/${SERVICE_NAME}"
DST="${HOME}/.config/systemd/user/${SERVICE_NAME}"

mkdir -p "${HOME}/.config/systemd/user" /home/bonsaihorn/Projects/wems-mcp-server/reports
cp "${SRC}" "${DST}"

systemctl --user daemon-reload
systemctl --user enable --now "${SERVICE_NAME}"

echo "Installed and started ${SERVICE_NAME}"
systemctl --user --no-pager --full status "${SERVICE_NAME}" | sed -n '1,20p'
