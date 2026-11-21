#!/usr/bin/env bash
# Run every Fusion component's unit tests. Pure stdlib; no network, no deps.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
fail=0
for comp in compatibility-manager optimizer benchmarks gaming-shell hardware setup; do
    dir="$HERE/$comp"
    [ -d "$dir/tests" ] || continue
    echo "== $comp =="
    ( cd "$dir" && python3 -m unittest discover -s tests ) || fail=1
    echo
done
if [ "$fail" = 0 ]; then
    echo "ALL FUSION TESTS PASSED"
else
    echo "SOME TESTS FAILED" >&2
fi
exit "$fail"
