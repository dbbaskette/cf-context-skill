#!/usr/bin/env bash
# Install the cf-context skill into the global skill directories for
# Claude Code and Cursor. Idempotent — re-run to update.
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/cf-context"

install_to() {
  local dest_root="$1" label="$2"
  if [ -d "$dest_root" ] || mkdir -p "$dest_root" 2>/dev/null; then
    mkdir -p "$dest_root/cf-context"
    cp -R "$SRC/." "$dest_root/cf-context/"
    echo "  ✓ $label → $dest_root/cf-context/"
  else
    echo "  ⚠ skipped $label ($dest_root not writable)"
  fi
}

echo "Installing cf-context skill:"
install_to "$HOME/.claude/skills"        "Claude Code"
install_to "$HOME/.cursor/skills-cursor" "Cursor"
echo "Done. Start a fresh session and try a 'cf' command."
