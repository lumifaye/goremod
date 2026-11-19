#!/usr/bin/env bash
set -eu
root="$(cd "$(dirname "$0")/.." && pwd)"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
if [ -d "$root/staging/WiiU" ]; then
    source_root="$root/staging/WiiU"
else
    source_root="$(cd "$root/.." && pwd)/WiiU"
fi
src="$source_root/third_party/libjuice/src"
cc -std=gnu11 -Wall -Wextra -Werror -D__XSDK__ -I"$src" \
    "$root/tests/net_compat_test.c" "$src/xbox360_compat.c" -o "$tmp/test"
"$tmp/test"
