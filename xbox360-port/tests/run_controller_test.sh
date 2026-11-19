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
mkdir -p "$tmp/pc/controller" "$tmp/lib/src"
cp "$source_root/src/pc/controller/controller_xbox360.c" \
   "$source_root/src/pc/controller/controller_xbox360.h" \
   "$source_root/src/pc/controller/controller_entry_point.c" "$tmp/pc/controller/"
cp "$game_root/src/pc/controller/controller_api.h" "$tmp/pc/controller/"
printf '#include <stdbool.h>\nextern bool configDisableGamepads;\nextern unsigned int configGamepadNumber;\nextern unsigned int configRumbleStrength;\n' > "$tmp/pc/configfile.h"
cat > "$tmp/ultra64.h" <<'HDR'
#ifndef MOCK_ULTRA64_H
#define MOCK_ULTRA64_H
#include <stdint.h>
typedef uint32_t u32; typedef int32_t s32; typedef uint8_t u8;
typedef struct { int dummy; } OSMesgQueue; typedef struct { int dummy; } OSContStatus;
typedef struct { uint16_t button; int8_t stick_x, stick_y, ext_stick_x, ext_stick_y; uint8_t errnum; } OSContPad;
#define A_BUTTON 0x8000
#define B_BUTTON 0x4000
#define Z_TRIG 0x2000
#define START_BUTTON 0x1000
#define U_JPAD 0x0800
#define D_JPAD 0x0400
#define L_JPAD 0x0200
#define R_JPAD 0x0100
#define L_TRIG 0x0020
#define R_TRIG 0x0010
#define U_CBUTTONS 0x0008
#define D_CBUTTONS 0x0004
#define L_CBUTTONS 0x0002
#define R_CBUTTONS 0x0001
#endif
HDR
printf '#include <ultra64.h>\n' > "$tmp/lib/src/libultra_internal.h"
printf '#include <ultra64.h>\n' > "$tmp/lib/src/osContInternal.h"
printf '#define UNUSED __attribute__((unused))\n' > "$tmp/macros.h"
cc -std=c11 -Wall -Wextra -Werror -DTARGET_XBOX360 -D__XSDK__ \
    -I"$root/tests/xsdk_mock" -I"$tmp" -I"$tmp/pc/controller" \
    "$root/tests/controller_test.c" "$tmp/pc/controller/controller_xbox360.c" \
    "$tmp/pc/controller/controller_entry_point.c" -o "$tmp/test"
"$tmp/test"
echo 'Xbox controller mapping tests passed (mock XAM; not hardware)'
