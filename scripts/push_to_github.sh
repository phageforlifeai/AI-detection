#!/usr/bin/env bash
set -euo pipefail

# Helper script to publish SciGram to your GitHub account.
# Usage Option 1 (with GitHub CLI `gh` installed & logged in):
#   ./scripts/push_to_github.sh scigram --public
#
# Usage Option 2 (with an empty repo URL created at https://github.com/new):
#   ./scripts/push_to_github.sh https://github.com/<your-username>/scigram.git

TARGET="${1:-https://github.com/phageforlifeai/AI-detection.git}"
VISIBILITY="${2:---public}"

if [ ! -d .git ]; then
  git init -b main
fi

git add -A
if ! git diff --cached --quiet; then
  git commit -m "Initial commit: SciGram AI detector & scientific structure analyzer"
fi

if [[ "$TARGET" == http://* || "$TARGET" == https://* || "$TARGET" == git@* ]]; then
  if git remote get-url origin >/dev/null 2>&1; then
    git remote set-url origin "$TARGET"
  else
    git remote add origin "$TARGET"
  fi
  git branch -M main
  git push -u origin main
  echo "Successfully pushed SciGram to $TARGET"
else
  if command -v gh >/dev/null 2>&1; then
    gh repo create "$TARGET" "$VISIBILITY" --source=. --remote=origin --push
  else
    echo "GitHub CLI (gh) not found. Create an empty repo at https://github.com/new and run:"
    echo "  ./scripts/push_to_github.sh https://github.com/<your-username>/$TARGET.git"
    exit 1
  fi
fi
