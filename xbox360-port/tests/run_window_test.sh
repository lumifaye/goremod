#!/usr/bin/env bash
set -eu
root="$(cd "$(dirname "$0")/.." && pwd)"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
if [ -d "$root/staging/WiiU" ]; then
    source_root="$root/staging/WiiU"
    game_root="$root/references/lumifaye/goremod/WiiU"
else
    game_root="$(cd "$root/.." && pwd)/WiiU"
    source_root="$game_root"
fi
cp "$source_root/src/pc/gfx/gfx_xbox360_window.c" \
   "$source_root/src/pc/gfx/gfx_xbox360_window.h" "$tmp/"
cp "$game_root/src/pc/gfx/gfx_window_manager_api.h" "$tmp/"
cc -std=gnu11 -Wall -Wextra -Werror -DTARGET_XBOX360 -D__XSDK__ \
    -I"$root/tests/xsdk_mock" -I"$tmp" \
    "$root/tests/window_test.c" "$tmp/gfx_xbox360_window.c" -o "$tmp/test"
"$tmp/test"
echo 'xSDK window lifecycle mocks: passed (not a renderer)'
