#!/usr/bin/env bash

set -euo pipefail

# shellcheck disable=SC1091
source "$(dirname "$0")/common.sh"

info "Updating agent-workbench"
update_workbench_checkout

AGENT_WORKBENCH_SKIP_EXTERNAL_SKILLS=1 "$(dirname "$0")/install.sh"
success "agent-workbench updated"
