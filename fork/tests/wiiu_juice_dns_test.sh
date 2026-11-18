set -eu
root="$(cd "$(dirname "$0")/../.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
cp "$root/WiiU/third_party/libjuice/src/wiiu_compat.c" "$tmp/wiiu_compat.c"
cc -std=gnu11 -D__WIIU__ -ffunction-sections -fdata-sections \
 -I"$root/fork/tests/wiiu_juice_dns_mock" -I"$root/fork/tests/coopnet_cemu_mock" \
 "$root/fork/tests/wiiu_juice_dns_test.c" "$tmp/wiiu_compat.c" \
 -Wl,--gc-sections -o "$tmp/test"
"$tmp/test"
