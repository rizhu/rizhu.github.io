#!/usr/bin/env bash
# Serve this site locally, exactly as GitHub Pages will serve it.
#
#   ./serve.sh          -> http://localhost:4000
#   ./serve.sh 8080     -> http://localhost:8080
#
# The only requirement is Python 3, which ships with macOS and most Linux
# distributions. There is nothing to install and nothing to build: the files in
# this directory are the website.

set -euo pipefail

cd "$(dirname "$0")"

PORT="${1:-4000}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found. Any static file server works, e.g.:" >&2
  echo "  npx --yes serve .   or   ruby -run -e httpd . -p ${PORT}" >&2
  exit 1
fi

echo "Serving $(pwd)"
echo "  http://localhost:${PORT}"
echo "Press Ctrl-C to stop."

exec python3 -m http.server "${PORT}" --bind 127.0.0.1
