#!/usr/bin/env bash

set -euo pipefail

# shellcheck disable=SC1091
source "$(dirname "$0")/common.sh"
# shellcheck disable=SC1091
source "$(dirname "$0")/setup/codex-external-skills.sh"

info "Updating agent-workbench"
update_workbench_checkout

if [ "${AGENT_WORKBENCH_SKIP_EXTERNAL_UPDATE:-0}" != "1" ]; then
    update_external_codex_skills
fi

"$(dirname "$0")/install.sh"
success "agent-workbench updated"
