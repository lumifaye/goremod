set -eu
root="$(cd "$(dirname "$0")/../.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
juice="$root/WiiU/third_party/libjuice/src"
coop="$root/WiiU/third_party/coopnet"
tests="$root/fork/tests"
cc -O2 -std=gnu11 -I"$juice" "$tests/wiiu_peer_hash_vectors.c" "$juice/hash.c" "$juice/hmac.c" -o "$tmp/hash"
"$tmp/hash"
c++ -std=gnu++17 -ffunction-sections -fdata-sections -I"$coop/common" -I"$coop/lib/include" \
 "$tests/wiiu_peer_flow_test.cpp" "$coop/common/peer.cpp" -Wl,--gc-sections -o "$tmp/peer"
"$tmp/peer"
cc -O2 -std=gnu11 -DJUICE_ENABLE_LOCALHOST_ADDRESS=1 -I"$juice" -I"$coop/lib/include/juice" -pthread \
 "$tests/wiiu_juice_pair_test.c" "$juice"/*.c -lm -o "$tmp/pair"
"$tmp/pair"
cc -O2 -std=gnu11 -I"$juice" -I"$coop/lib/include/juice" -pthread \
 "$tests/wiiu_stun_packet_test.c" "$juice"/*.c -lm -o "$tmp/stun"
"$tmp/stun"
if [ -n "${PPC_CC:-}" ] && [ -n "${QEMU_PPC:-}" ]; then
 "$PPC_CC" -O2 -mcpu=750 -mhard-float -fno-builtin -ffunction-sections -fdata-sections \
  -DPPC_FREESTANDING -DNDEBUG -nostdlib -Wl,--gc-sections,-e,_start -I"$juice" \
  "$tests/wiiu_peer_hash_vectors.c" "$juice/hash.c" "$juice/hmac.c" -o "$tmp/hash-ppc"
 "$QEMU_PPC" "$tmp/hash-ppc"
 echo 'big-endian PowerPC SHA-1, HMAC and STUN wire vectors: ok'
fi
cc -O2 -std=gnu11 -DJUICE_NO_IPV6 -I"$juice" -I"$coop/lib/include/juice" -pthread \
 "$tests/wiiu_ipv4_candidate_test.c" "$juice"/*.c -lm -o "$tmp/ipv4"
"$tmp/ipv4"
echo 'hash vectors, peer state/order, and bidirectional ICE: ok'
