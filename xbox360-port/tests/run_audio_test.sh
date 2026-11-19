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
cp "$source_root/src/pc/audio/audio_xbox360.c" "$source_root/src/pc/audio/audio_xbox360.h" "$tmp/"
cp "$game_root/src/pc/audio/audio_api.h" "$tmp/"
cc -std=c11 -Wall -Wextra -Werror -DTARGET_XBOX360 -D__XSDK__ \
    -I"$root/tests/xsdk_mock" -I"$tmp" \
    "$root/tests/audio_test.c" "$tmp/audio_xbox360.c" -lm -o "$tmp/test"
"$tmp/test"
