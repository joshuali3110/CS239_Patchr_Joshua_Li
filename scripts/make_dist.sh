#!/usr/bin/env bash
# Build the two CS239 submission archives from the committed HEAD.
#
#   scripts/make_dist.sh <uid>
#
# Produces, in dist/:
#   Joshua_Li-Patchr-<uid>-requirements.tar.gz   Patchr/ (app, policy, tools, agents, episodes)
#   Joshua_Li-Patchr-<uid>-whole.tar.gz          the whole repository (src/, tests/, docs, traces)
#
# Archives come from `git archive HEAD`, so only committed, tracked files are
# included: .env, .runs/ and other untracked files can never leak into them.
set -euo pipefail

NAME="Joshua_Li"
APP="Patchr"
STUDENT_UID="${1:-}"   # not $UID: bash reserves that for the numeric user id

if [[ -z "$STUDENT_UID" ]]; then
  echo "usage: $0 <uid>" >&2
  exit 2
fi
if [[ ! "$STUDENT_UID" =~ ^[0-9]{9}$ ]]; then
  echo "error: expected a 9-digit UCLA UID, got '$STUDENT_UID'" >&2
  exit 2
fi

cd "$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
if [[ -n "$(git status --porcelain)" ]]; then
  echo "warning: the working tree has uncommitted or untracked changes; they are NOT included" >&2
fi

mkdir -p dist
REQ="dist/${NAME}-${APP}-${STUDENT_UID}-requirements.tar.gz"
WHOLE="dist/${NAME}-${APP}-${STUDENT_UID}-whole.tar.gz"
git archive --format=tar.gz -o "$REQ" HEAD "$APP"
git archive --format=tar.gz -o "$WHOLE" HEAD

check() {  # check <archive> <required path>...
  local archive=$1; shift
  local listing
  listing=$(tar -tzf "$archive")
  for path in "$@"; do
    grep -qx -- "$path" <<<"$listing" || { echo "error: $archive is missing $path" >&2; exit 1; }
  done
  if grep -qE '(^|/)\.env$|(^|/)\.runs/' <<<"$listing"; then
    echo "error: $archive contains .env or .runs/" >&2
    exit 1
  fi
}

check "$REQ" "$APP/app.md" "$APP/policy.md" "$APP/tools.md" \
  "$APP/agents/triage.md" "$APP/agents/fixer.md" "$APP/agents/reviewer.md" "$APP/agents/release.md" \
  "$APP/episodes/S1-happy-path.md"
check "$WHOLE" "src/README.md" "tests/README.md" "requirements.md" "policies.md" "traces/README.md" \
  "LICENSE" "pyproject.toml" "uv.lock" "$APP/policy.md"

echo "Built from commit $(git rev-parse --short HEAD):"
for archive in "$REQ" "$WHOLE"; do
  echo "  $archive  ($(tar -tzf "$archive" | grep -vc '/$') files, $(du -h "$archive" | cut -f1))"
done
