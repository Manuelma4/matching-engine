#!/usr/bin/env bash
# Benchmark protocol: RUNS process launches, each running every variant on every regime.
# The variant order alternates between launches (ABAB, then BABA) so drift in thermal or
# scheduler state does not favour one variant. Raw rows and the environment are written
# to docs/bench/<date>/, then summarised.
#
#   bench/run.sh            # 10 launches, all variants and regimes
#   RUNS=3 OPS=200000 bench/run.sh
set -euo pipefail

cd "$(dirname "$0")/.."
RUNS=${RUNS:-10}
OPS=${OPS:-1000000}
SEED=${SEED:-42}
BIN=${BIN:-build/me_bench}
OUT=${OUT:-docs/bench/$(date +%F)}

help_status=0
help_text=$("$BIN" --help 2>&1) || help_status=$?
# Older me_bench versions print usage and return 2 for --help.
if [[ $help_status != 0 && $help_status != 2 ]]; then
    printf '%s --help failed with status %s\n' "$BIN" "$help_status" >&2
    exit "$help_status"
fi
books=$(printf '%s\n' "$help_text" | sed -n 's/^  books: //p')
read -r -a order <<<"$books"
if [[ -z "${order[0]:-}" ]]; then
    printf 'No book variants found in %s --help\n' "$BIN" >&2
    exit 2
fi
mkdir -p "$OUT"
stage=$(mktemp -d "$OUT/.run.XXXXXXXX")
cleanup() {
    for report in env.txt raw.csv summary.md; do
        if [[ -f "$stage/$report" ]]; then unlink "$stage/$report"; fi
    done
    rmdir "$stage"
}
trap cleanup EXIT

commit=$(git rev-parse HEAD)
if ! git diff --quiet || ! git diff --cached --quiet; then
    commit+="-dirty"
fi

{
    echo "date:     $(date -u +%FT%TZ)"
    echo "commit:   $commit"
    echo "machine:  $(sysctl -n machdep.cpu.brand_string 2>/dev/null || uname -m)"
    echo "cores:    $(sysctl -n hw.perflevel0.physicalcpu 2>/dev/null || echo ?)P + $(sysctl -n hw.perflevel1.physicalcpu 2>/dev/null || echo ?)E"
    echo "os:       $(sw_vers -productName 2>/dev/null) $(sw_vers -productVersion 2>/dev/null)"
    echo "compiler: $(c++ --version | head -1)"
    echo "power:    $(pmset -g batt 2>/dev/null | head -1 | sed "s/.*'\(.*\)'.*/\1/")"
    echo "powermode: $(pmset -g 2>/dev/null | awk '/lowpowermode|powermode/ {print $2; exit}') (0 = automatic, 1 = low power)"
    echo "runs:     $RUNS launches x ${#order[@]} variants, $OPS ops, seed $SEED"
} >"$stage/env.txt"

echo "book,regime,seed,ops,hash,peak_orders,mops,op,count,p50,p90,p99,p999,max,max_orders" >"$stage/raw.csv"
for ((run = 1; run <= RUNS; run++)); do
    for ((position = 0; position < ${#order[@]}; position++)); do
        index=$position
        if ((run % 2 == 0)); then
            index=$((${#order[@]} - 1 - position))
        fi
        "$BIN" --book "${order[$index]}" --regime all --ops "$OPS" --seed "$SEED" --csv >>"$stage/raw.csv"
    done
    echo "run $run/$RUNS done" >&2
done

python3 bench/summarize.py "$stage/raw.csv" --launches "$RUNS" >"$stage/summary.md" || {
    status=$?
    cat "$stage/summary.md" >&2
    exit "$status"
}
for report in env.txt raw.csv summary.md; do
    mv -f "$stage/$report" "$OUT/$report"
done
cat "$OUT/summary.md"
