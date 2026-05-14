#!/usr/bin/env bash
# install-all.sh — install the agent-collab-workspace plugin from the
# agent-collab-skills marketplace. The marketplace ships exactly one
# bundle plugin that contains all 6 skills.
#
# Usage:
#   bash scripts/install-all.sh
#
# Default scope is `user` (this OS account, all projects). Pass
# `--scope project` as the first argument to install only for the
# current project.

set -euo pipefail

MARKETPLACE="WenyuChiou/agent-collab-skills"
PLUGIN="agent-collab-workspace"

SCOPE="user"
if [[ "${1:-}" == "--scope" && -n "${2:-}" ]]; then
  SCOPE="$2"
fi

if ! command -v claude >/dev/null 2>&1; then
  echo "error: 'claude' CLI not found on PATH." >&2
  echo "Install Claude Code first: https://claude.ai/code" >&2
  exit 1
fi

echo ">> Adding marketplace: $MARKETPLACE"
claude plugin marketplace add "$MARKETPLACE"

echo ""
echo ">> Installing $PLUGIN (scope: $SCOPE)"
claude plugin install "$PLUGIN@agent-collab-skills" --scope "$SCOPE"

echo ""
echo "Done. Run 'claude plugin list' to confirm:"
echo "  agent-collab-workspace@agent-collab-skills  Status: ✔ enabled"
echo ""
echo "6 skills are now available:"
echo "  - agent-task-splitter"
echo "  - agent-context-budget"
echo "  - agent-output-reconciler"
echo "  - agent-debate"
echo "  - agent-shared-memory"
echo "  - agent-acceptance-gate"
