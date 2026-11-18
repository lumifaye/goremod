set -eu
root="$(cd "$(dirname "$0")/../.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
common="$root/WiiU/third_party/coopnet/common"
c++ -std=c++17 -D__WIIU__ -ffunction-sections -fdata-sections \
  -I"$root/fork/tests/coopnet_cemu_mock" -I"$common" \
  -I"$root/WiiU/third_party/coopnet/lib/include" \
  "$root/fork/tests/coopnet_cemu_test.cpp" "$common/socket.cpp" "$common/utils.cpp" \
  -Wl,--gc-sections -o "$tmp/test"
"$tmp/test"
