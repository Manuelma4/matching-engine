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

mkdir -p "$OUT"
books=$("$BIN" --help 2>&1 | sed -n 's/^  books: //p' || true)
read -r -a order <<<"$books"

{
    echo "date:     $(date -u +%FT%TZ)"
    echo "commit:   $(git rev-parse --short HEAD)$(git diff --quiet || echo '-dirty')"
    echo "machine:  $(sysctl -n machdep.cpu.brand_string 2>/dev/null || uname -m)"
    echo "cores:    $(sysctl -n hw.perflevel0.physicalcpu 2>/dev/null || echo ?)P + $(sysctl -n hw.perflevel1.physicalcpu 2>/dev/null || echo ?)E"
    echo "os:       $(sw_vers -productName 2>/dev/null) $(sw_vers -productVersion 2>/dev/null)"
    echo "compiler: $(c++ --version | head -1)"
    echo "power:    $(pmset -g batt 2>/dev/null | head -1 | sed "s/.*'\(.*\)'.*/\1/")"
    echo "powermode: $(pmset -g 2>/dev/null | awk '/lowpowermode|powermode/ {print $2; exit}') (0 = automatic, 1 = low power)"
    echo "runs:     $RUNS launches x ${#order[@]} variants, $OPS ops, seed $SEED"
} >"$OUT/env.txt"

echo "book,regime,seed,ops,hash,peak_orders,mops,op,count,p50,p90,p99,p999,max" >"$OUT/raw.csv"
for ((run = 1; run <= RUNS; run++)); do
    if ((run % 2 == 0)); then
        sequence=$(printf '%s\n' "${order[@]}" | tail -r)
    else
        sequence=$(printf '%s\n' "${order[@]}")
    fi
    for book in $sequence; do
        "$BIN" --book "$book" --regime all --ops "$OPS" --seed "$SEED" --csv >>"$OUT/raw.csv"
    done
    echo "run $run/$RUNS done" >&2
done

python3 bench/summarize.py "$OUT/raw.csv" >"$OUT/summary.md"
cat "$OUT/summary.md"
