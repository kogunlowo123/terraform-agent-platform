#!/usr/bin/env bash
# TAP release helper: bump versions, update the bundle manifest, tag, and
# (optionally) push. The tag push triggers .github/workflows/release.yml.
#
# Usage:
#   ./scripts/release.sh patch|minor|major [--push]
#   ./scripts/release.sh 1.4.2 [--push]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

log() { printf '\033[1;32m[release]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[release]\033[0m %s\n' "$*" >&2; exit 1; }

BUMP="${1:-}"
PUSH=false
[[ "${2:-}" == "--push" ]] && PUSH=true
[[ -n "$BUMP" ]] || die "usage: release.sh patch|minor|major|X.Y.Z [--push]"

git diff --quiet && git diff --cached --quiet || die "working tree is dirty; commit or stash first"

current=$(git describe --tags --abbrev=0 --match 'v*' 2>/dev/null | sed 's/^v//' || echo "0.0.0")
IFS=. read -r major minor patch <<<"$current"

case "$BUMP" in
    major) next="$((major + 1)).0.0" ;;
    minor) next="${major}.$((minor + 1)).0" ;;
    patch) next="${major}.${minor}.$((patch + 1))" ;;
    *)
        [[ "$BUMP" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "not a bump keyword or semver: $BUMP"
        next="$BUMP"
        ;;
esac

log "Current version: v$current -> next: v$next"

# 1. pyproject versions (platform, sdk when present)
for proj in platform sdk; do
    f="$proj/pyproject.toml"
    if [[ -f "$f" ]]; then
        sed -i.bak -E "s/^version = \"[0-9]+\.[0-9]+\.[0-9]+\"/version = \"$next\"/" "$f" && rm -f "$f.bak"
        log "Bumped $f"
    fi
done

# 2. policy bundle manifest
bundle="governance/bundles/bundle.yaml"
if [[ -f "$bundle" ]]; then
    sed -i.bak -E "s/^(  version: )[0-9]+\.[0-9]+\.[0-9]+.*/\1$next            # bumped by scripts\/release.sh/" "$bundle" && rm -f "$bundle.bak"
    log "Bumped $bundle"
fi

# 3. sanity: tests must pass before tagging
if command -v opa >/dev/null; then
    log "Running opa test policies/"
    opa test policies/ >/dev/null || die "policy tests failed"
else
    log "opa not installed — skipping policy tests (CI will enforce)"
fi

# 4. commit + tag
git add -A
git commit -m "release: v$next"
git tag -a "v$next" -m "TAP v$next"
log "Tagged v$next"

if $PUSH; then
    git push origin HEAD "v$next"
    log "Pushed; release pipeline is running"
else
    log "Dry-run complete. Push with: git push origin HEAD v$next"
fi
