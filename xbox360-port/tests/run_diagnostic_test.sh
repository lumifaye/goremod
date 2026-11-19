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
mkdir -p "$tmp/pc/controller" "$tmp/pc/audio"
cp "$source_root/src/pc/controller/controller_xbox360.c" \
   "$source_root/src/pc/controller/controller_xbox360.h" "$tmp/pc/controller/"
cp "$game_root/src/pc/controller/controller_api.h" "$tmp/pc/controller/"
cp "$source_root/src/pc/audio/audio_xbox360.c" "$source_root/src/pc/audio/audio_xbox360.h" "$tmp/pc/audio/"
cp "$game_root/src/pc/audio/audio_api.h" "$tmp/pc/audio/"
printf '#include <stdbool.h>\nextern bool configDisableGamepads;\nextern unsigned int configGamepadNumber;\n' > "$tmp/pc/configfile.h"
I="-I$root/tests/xsdk_mock -I$root/diagnostic/include -I$tmp/pc/controller -I$tmp/pc/audio"
cc -std=gnu11 -Wall -Wextra -Werror -DTARGET_XBOX360 -D__XSDK__ -Dmain=diagnostic_main $I \
    -c "$root/diagnostic/main.c" -o "$tmp/main.o"
cc -std=gnu11 -Wall -Wextra -Werror -DTARGET_XBOX360 -D__XSDK__ $I \
    "$root/tests/diagnostic_test.c" "$tmp/pc/controller/controller_xbox360.c" \
    "$tmp/pc/audio/audio_xbox360.c" "$tmp/main.o" -o "$tmp/test"
"$tmp/test"
echo 'Diagnostic loop/controller/audio mocked integration: passed'
