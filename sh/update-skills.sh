#!/usr/bin/env bash

set -euo pipefail

# shellcheck disable=SC1091
source "$(dirname "$0")/common.sh"
# shellcheck disable=SC1091
source "$(dirname "$0")/setup/codex-external-skills.sh"

update_external_codex_skills
success "External Codex skill update check complete"
