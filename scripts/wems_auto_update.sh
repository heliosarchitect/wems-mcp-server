#!/usr/bin/env bash
set -euo pipefail

REPO="${WEMS_REPO:-$HOME/Projects/wems-mcp-server}"
BRANCH="${WEMS_BRANCH:-master}"
REMOTE="${WEMS_REMOTE:-origin}"
LOG_DIR="$REPO/reports"
LOG_FILE="$LOG_DIR/wems_auto_update.log"

mkdir -p "$LOG_DIR"

ts() { date '+%Y-%m-%d %H:%M:%S %Z'; }
log() { echo "[$(ts)] $*" | tee -a "$LOG_FILE"; }

cd "$REPO"

# safety: don't auto-pull over local uncommitted work
if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  log "SKIP: working tree dirty (tracked changes present); auto-update paused"
  exit 0
fi

git fetch "$REMOTE" "$BRANCH" --quiet
LOCAL_SHA="$(git rev-parse HEAD)"
REMOTE_SHA="$(git rev-parse "$REMOTE/$BRANCH")"

if [[ "$LOCAL_SHA" == "$REMOTE_SHA" ]]; then
  log "NOOP: already up to date ($LOCAL_SHA)"
  exit 0
fi

log "UPDATE: $LOCAL_SHA -> $REMOTE_SHA"
PREV_SHA="$LOCAL_SHA"

# fast-forward only to avoid unsafe merges
if ! git merge --ff-only "$REMOTE/$BRANCH" >/dev/null 2>&1; then
  log "FAIL: fast-forward merge refused; manual intervention required"
  exit 1
fi

# QA gate
if ! ./.venv-release/bin/pytest -q tests >/tmp/wems-auto-update-pytest.log 2>&1; then
  log "FAIL: QA gate failed; rolling back to $PREV_SHA"
  git reset --hard "$PREV_SHA" >/dev/null
  cat /tmp/wems-auto-update-pytest.log >> "$LOG_FILE"
  exit 1
fi

# restart runtime components on success
systemctl --user restart wems-unified-relay.service || true
log "OK: deployed $REMOTE_SHA; QA passed; relay restarted"
