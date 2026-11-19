#!/usr/bin/env bash
set -eu
root="$(cd "$(dirname "$0")/.." && pwd)"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
if [ -d "$root/staging/WiiU" ]; then
    source_root="$root/staging/WiiU"
else
    source_root="$(cd "$root/.." && pwd)/WiiU"
fi
mkdir -p "$tmp/network/packets"
cp "$root/tests/mock_network/network.h" "$tmp/network/network.h"
cp "$source_root/src/pc/network/packets/packet_read_write.c" "$tmp/network/packets/"
common="-I$root/tests/include -I$tmp/network"
cc -std=c11 -Wall -Wextra -Werror $common "$root/tests/packet_test.c" \
    "$tmp/network/packets/packet_read_write.c" -o "$tmp/test-native"
"$tmp/test-native"
if [ -n "${PPC_CC:-}" ] && [ -n "${QEMU_PPC:-}" ]; then
    "$PPC_CC" -std=c11 -O2 -mcpu=750 -mhard-float -fno-builtin -ffunction-sections \
        -fdata-sections -DTARGET_XBOX360 -DPPC_FREESTANDING -nostdlib \
        -Wl,--gc-sections,-e,_start $common "$root/tests/packet_test.c" \
        "$tmp/network/packets/packet_read_write.c" -o "$tmp/test-ppc"
    timeout 10 "$QEMU_PPC" "$tmp/test-ppc"
    echo 'PowerPC big-endian Xbox-target packet vectors passed'
fi
echo 'Native little-endian packet vectors passed'
