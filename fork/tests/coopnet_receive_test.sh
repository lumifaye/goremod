set -eu
root="$(cd "$(dirname "$0")/../.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
c++ -std=c++17 -D__WIIU__ -ffunction-sections -fdata-sections \
    -I"$root/WiiU/third_party/coopnet/common" \
    -I"$root/WiiU/third_party/coopnet/lib/include" \
    "$root/fork/tests/coopnet_receive_test.cpp" \
    "$root/WiiU/third_party/coopnet/common/connection.cpp" \
    -Wl,--gc-sections -Wl,--wrap=recv -Wl,--wrap=send -o "$tmp/test"
"$tmp/test"
