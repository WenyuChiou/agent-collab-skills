# install-all.ps1 — install the agent-collab-workspace plugin from the
# agent-collab-skills marketplace.
#
# Usage:
#   pwsh scripts/install-all.ps1
#   pwsh scripts/install-all.ps1 -Scope project

param(
  [ValidateSet("user", "project", "local")]
  [string]$Scope = "user"
)

$ErrorActionPreference = "Stop"

$Marketplace = "WenyuChiou/agent-collab-skills"
$Plugin = "agent-collab-workspace"

if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
  Write-Error "'claude' CLI not found on PATH. Install Claude Code first: https://claude.ai/code"
  exit 1
}

Write-Host ">> Adding marketplace: $Marketplace"
claude plugin marketplace add $Marketplace

Write-Host ""
Write-Host ">> Installing $Plugin (scope: $Scope)"
claude plugin install "$Plugin@agent-collab-skills" --scope $Scope

Write-Host ""
Write-Host "Done. Run 'claude plugin list' to confirm."
Write-Host ""
Write-Host "5 skills are now available:"
Write-Host "  - agent-task-splitter"
Write-Host "  - agent-output-reconciler"
Write-Host "  - agent-debate"
Write-Host "  - agent-shared-memory"
Write-Host "  - agent-acceptance-gate"
