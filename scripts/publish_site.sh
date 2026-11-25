#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
REMOTE="$(git -C "$ROOT" remote get-url origin)"
python3 "$ROOT/scripts/build_web.py" --check
TMP="$(mktemp -d)"
cp -R "$ROOT/web/." "$TMP/"
touch "$TMP/.nojekyll"
cd "$TMP"
git init -q
git checkout -q -b gh-pages
git add -A
git commit -q -m "Publish site"
git push -f "$REMOTE" gh-pages
echo "Selesai."
