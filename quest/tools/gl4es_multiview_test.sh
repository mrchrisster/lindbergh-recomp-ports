#!/bin/sh
# Host test of quest/gl4es.patch's multiview copy-back slots (see the .c).
# Needs the patched gl4es source: $DEPS/gl4es (quest/deps.sh).
set -e
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
G=${DEPS:-$ROOT/../deps}/gl4es
OUT=${TMPDIR:-/tmp}/gl4es_multiview_test.$$
cc -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer -w -I"$G/include" -I"$G/src" -I"$G/src/gl" \
    "$ROOT/quest/tools/gl4es_multiview_test.c" "$G/src/gl/multiview.c" -o "$OUT"
"$OUT" | grep -v '^LIBGL'
rm -f "$OUT"
