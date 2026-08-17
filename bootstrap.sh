#!/usr/bin/env bash
#
# One-time setup after cloning. Run from the repository root:
#   ./bootstrap.sh

set -e

root="$(git rev-parse --show-toplevel)"
cd "$root"

# Install the pre-commit hook
ln -sf ../../tools/hooks/pre-commit .git/hooks/pre-commit
echo "Installed pre-commit hook."

echo "Done."
