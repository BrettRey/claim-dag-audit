#!/usr/bin/env bash
# Re-audit one or more claim-dag audit directories on a schedule. Each run
# re-attacks currently-cleared targets with a stronger ladder and appends any
# demotions to that directory's drift-log.yaml (the calibration loop in
# docs/llm-runner.md). Under subscription auth the cost is CLI invocations, not
# dollars, so pace this to your Claude Code / Codex message windows.
#
# Usage:   reaudit-cron.sh <audit_dir> [<audit_dir> ...]
# Env:     CLAIM_DAG_K   independent families required to clear (default 2)
#
# Crontab example (weekly, Sundays 02:30 local):
#   30 2 * * 0 /ABS/PATH/tools/claim-dag-audit/scripts/reaudit-cron.sh \
#     /ABS/PATH/papers/preprints/kinds-as-projectibility-profiles/audits/claim-dag/2026-07-05 \
#     >> "$HOME/claim-dag-reaudit.log" 2>&1
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "usage: $(basename "$0") <audit_dir> [<audit_dir> ...]" >&2
  exit 2
fi

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "$HERE/.venv/bin/activate"

status=0
for dir in "$@"; do
  echo "=== $(date -u +%FT%TZ) reaudit ${dir} ==="
  if ! claim-dag-run reaudit "$dir" --k "${CLAIM_DAG_K:-2}"; then
    echo "reaudit FAILED for ${dir}" >&2
    status=1
  fi
done
exit "$status"
