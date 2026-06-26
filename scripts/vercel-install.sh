#!/usr/bin/env bash
set -euo pipefail

DESIGN_SYSTEM_DIR="../platform-design-system"
DESIGN_SYSTEM_REPO="https://github.com/kushalsamant/platform-design-system.git"

if [ ! -d "${DESIGN_SYSTEM_DIR}/package.json" ]; then
  git clone --depth 1 "${DESIGN_SYSTEM_REPO}" "${DESIGN_SYSTEM_DIR}"
fi

npm ci --prefix "${DESIGN_SYSTEM_DIR}"
npm run build --prefix "${DESIGN_SYSTEM_DIR}"
npm ci --prefix frontend
