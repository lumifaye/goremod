#!/usr/bin/env bash
# Build only a hardware diagnostic, not a game or a release.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
if [ -d "$root/staging/WiiU" ]; then
    source_root="$root/staging/WiiU"
    game_root="$root/references/lumifaye/goremod/WiiU"
else
    game_root="$(cd "$root/.." && pwd)/WiiU"
    source_root="$game_root"
fi
: "${XSDK_ROOT:?Set XSDK_ROOT to the pinned xSDK source tree}"
: "${XSDK_TOOLCHAIN:?Set XSDK_TOOLCHAIN to the xSDK compiler prefix}"
cc="$XSDK_TOOLCHAIN/bin/powerpc-xsdk-elf-gcc"
[ -x "$cc" ] || { echo 'xSDK compiler missing' >&2; exit 1; }
[ -f "$XSDK_ROOT/build/libxsdk.a" ] || { echo 'Build xSDK libxsdk.a first' >&2; exit 1; }
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/pc/controller" "$tmp/pc/audio"
cp "$source_root/src/pc/controller/controller_xbox360.c" \
   "$source_root/src/pc/controller/controller_xbox360.h" "$tmp/pc/controller/"
cp "$game_root/src/pc/controller/controller_api.h" "$tmp/pc/controller/"
cp "$source_root/src/pc/audio/audio_xbox360.c" "$source_root/src/pc/audio/audio_xbox360.h" "$tmp/pc/audio/"
cp "$game_root/src/pc/audio/audio_api.h" "$tmp/pc/audio/"
printf '#include <stdbool.h>\nextern bool configDisableGamepads;\nextern unsigned int configGamepadNumber;\n' > "$tmp/pc/configfile.h"
flags=(-mcpu=cell -fno-pic -O2 -g -std=gnu17 -Wall -Wextra -Werror -DTARGET_XBOX360 -D__XSDK__ -I"$XSDK_ROOT/include" -I"$root/diagnostic/include" -I"$tmp/pc/controller" -I"$tmp/pc/audio")
"$cc" "${flags[@]}" -c "$root/diagnostic/main.c" -o "$tmp/main.o"
"$cc" "${flags[@]}" -c "$tmp/pc/controller/controller_xbox360.c" -o "$tmp/controller.o"
"$cc" "${flags[@]}" -c "$tmp/pc/audio/audio_xbox360.c" -o "$tmp/audio.o"
mkdir -p "$root/diagnostic/output"
"$cc" -static -nostdlib -T "$XSDK_ROOT/src/xsdk.ld" -o "$tmp/diagnostic.elf" "$tmp/main.o" "$tmp/controller.o" "$tmp/audio.o" -Wl,--start-group "$XSDK_ROOT/build/libxsdk.a" -lc -lm -lgcc -Wl,--end-group
python3 "$XSDK_ROOT/tools/elf2xex.py" --title-name 'Realism64 Xbox 360 diagnostic' "$tmp/diagnostic.elf" "$root/diagnostic/output/diagnostic.xex"
echo "Built diagnostic only: $root/diagnostic/output/diagnostic.xex"
