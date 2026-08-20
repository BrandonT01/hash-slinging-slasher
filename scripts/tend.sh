#!/usr/bin/env bash
#
# Merges submission pull requests as they land, and deletes the branches behind them.
#
#     bash scripts/tend.sh            watch and tend, every 60 seconds
#     bash scripts/tend.sh --once     one pass and stop
#
# ## Why
#
# A grind opens a pull request after every job, so an overnight run leaves dozens. Each is the
# same shape, and reviewing them by eye is a queue rather than a judgement. This does the checking
# a person could not do by eye anyway, and merges what passes.
#
# ## What it will not merge
#
# Anything that is not submission text. A pull request touching `src/`, `bin/`, `data/`,
# `snapshots/`, `.github/` or the markdown at the root changes what every contributor runs, and
# that is a decision for a person. Those are left open and reported.
#
# A pull request carrying a **new or changed** generator is also left alone: a generator is code
# that every agent pulling this repository then runs, so it gets read by a human before it lands.
# What is removed automatically is a script copy identical to one already in the library --
# `submit` should no longer send those, but an older client or a stale `contrib/` still can, and
# merging one either duplicates a file or flips its line endings for nothing.
#
# The comparison is by **content**, not by name: a stamp differs on every submission, so names
# cannot tell an update from a duplicate, and those two need opposite treatment.
#
# ## Safety
#
# Every check is read from the GitHub API rather than from a checkout, so nothing in a fork's
# branch is executed here. Branches are deleted only after their tip is proved to be an ancestor
# of `main`, so an unmerged branch cannot be lost.
set -u

cd "$(dirname "$0")/.." || exit 1
mkdir -p logs

REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner 2>/dev/null \
       || echo "KingslayerKyle/hash-slinging-slasher")
ONCE=0
[ "${1:-}" = "--once" ] && ONCE=1

say() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }

tend_one() {
    local pr="$1"
    local files branch path name stem here sha candidate

    files=$(gh pr view "$pr" --repo "$REPO" --json files --jq '.files[].path' 2>/dev/null)
    [ -z "$files" ] && return 0

    if printf '%s\n' "$files" | grep -qvE '^(submissions/|scripts/contributed/)'; then
        say "#$pr touches more than submissions -- leaving it for a human"
        return 0
    fi

    branch=$(gh pr view "$pr" --repo "$REPO" --json headRefName --jq .headRefName 2>/dev/null)
    [ -z "$branch" ] && return 0

    for path in $(printf '%s\n' "$files" | grep '^scripts/contributed/'); do
        name=$(basename "$path")
        stem=$(echo "${name%.py}" | sed -E 's/_[0-9]{8}-[0-9]{6}$//')

        # Raw content straight from the API: no base64, no line-ending juggling.
        gh api -H "Accept: application/vnd.github.raw" \
            "repos/$REPO/contents/$path?ref=$branch" > logs/.incoming 2>/dev/null || continue

        here=""
        for candidate in scripts/contributed/"$stem"_*.py "scripts/contributed/$stem.py" "scripts/$stem.py"; do
            [ -f "$candidate" ] || continue
            # --strip-trailing-cr so a CRLF checkout does not read as a different file.
            if diff -q --strip-trailing-cr "$candidate" logs/.incoming >/dev/null 2>&1; then
                here="$candidate"
                break
            fi
        done
        rm -f logs/.incoming

        if [ -z "$here" ]; then
            say "#$pr carries a new or changed generator ($name) -- leaving it for a human"
            return 0
        fi

        sha=$(gh api "repos/$REPO/contents/$path?ref=$branch" --jq .sha 2>/dev/null)
        [ -z "$sha" ] && continue

        if gh api -X DELETE "repos/$REPO/contents/$path" \
               -f message="Already in the library as $here" \
               -f sha="$sha" -f branch="$branch" >/dev/null 2>&1; then
            say "#$pr dropped duplicate $name (library has $here)"
        fi
    done

    if gh pr merge "$pr" --repo "$REPO" --merge >/dev/null 2>&1; then
        say "#$pr merged"
    else
        say "#$pr would not merge -- probably a conflict, leaving it"
    fi
}

prune_branches() {
    local branch sha
    git fetch -q origin --prune 2>/dev/null

    for branch in $(git ls-remote --heads origin 'refs/heads/findings/*' 2>/dev/null \
                    | awk '{print $2}' | sed 's|refs/heads/||'); do
        sha=$(git ls-remote origin "refs/heads/$branch" 2>/dev/null | cut -f1)
        [ -z "$sha" ] && continue

        # Proved to be in main, never assumed. An unmerged branch is somebody's night.
        if git merge-base --is-ancestor "$sha" origin/main 2>/dev/null; then
            git push origin --delete "$branch" >/dev/null 2>&1 && say "deleted branch $branch"
        fi
    done
}

while :; do
    for pr in $(gh pr list --repo "$REPO" --json number --jq '.[].number' 2>/dev/null); do
        tend_one "$pr"
    done

    prune_branches

    [ "$ONCE" = "1" ] && break
    sleep 60
done
