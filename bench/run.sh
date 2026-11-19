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
for report in env.txt raw.csv summary.md; do
    path="$OUT/$report"
    if [[ -L "$path" || ( -e "$path" && ! -f "$path" ) ]]; then
        printf 'Invalid report destination: %s\n' "$path" >&2
        exit 2
    fi
done
stage=$(mktemp -d "$OUT/.run.XXXXXXXX")
keep_stage=0
cleanup() {
    if ((keep_stage)); then return; fi
    if [[ -d "$stage/captures" ]]; then
        rm -f "$stage"/captures/*
        rmdir "$stage/captures"
    fi
    for report in env.txt raw.csv summary.md; do
        if [[ -f "$stage/$report" ]]; then unlink "$stage/$report"; fi
    done
    if [[ -d "$stage/previous" ]]; then
        for report in env.txt raw.csv summary.md; do
            if [[ -f "$stage/previous/$report" ]]; then unlink "$stage/previous/$report"; fi
        done
        rmdir "$stage/previous"
    fi
    rmdir "$stage"
}
trap cleanup EXIT
mkdir "$stage/captures"

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
        capture="$run-$position.csv"
        printf '%s\t%s\n' "$capture" "${order[$index]}" >>"$stage/captures/index.tsv"
        "$BIN" --book "${order[$index]}" --regime all --ops "$OPS" --seed "$SEED" --csv >"$stage/captures/$capture"
    done
    echo "run $run/$RUNS done" >&2
done

python3 bench/summarize.py "$stage/raw.csv" --launches "$RUNS" \
    --capture-index "$stage/captures/index.tsv" --expected-ops "$OPS" --expected-seed "$SEED" >"$stage/summary.md" || {
    status=$?
    cat "$stage/summary.md" >&2
    exit "$status"
}
mkdir "$stage/previous"
for report in env.txt raw.csv summary.md; do
    if [[ -f "$OUT/$report" ]]; then cp -p "$OUT/$report" "$stage/previous/$report"; fi
done
promoted_count=0
keep_stage=1
for report in env.txt raw.csv summary.md; do
    if mv -f "$stage/$report" "$OUT/$report"; then
        promoted_count=$((promoted_count + 1))
    else
        promotion_status=$?
        restore_failed=0
        for previous in env.txt raw.csv summary.md; do
            if ((promoted_count == 0)); then break; fi
            promoted_count=$((promoted_count - 1))
            if [[ -f "$stage/previous/$previous" ]]; then
                if ! mv -f "$stage/previous/$previous" "$OUT/$previous"; then restore_failed=1; fi
            else
                if ! unlink "$OUT/$previous"; then restore_failed=1; fi
            fi
        done
        keep_stage=$restore_failed
        if ((restore_failed)); then
            printf 'Report rollback failed; recovery files retained at %s\n' "$stage/previous" >&2
        fi
        exit "$promotion_status"
    fi
done
keep_stage=0
cat "$OUT/summary.md"
