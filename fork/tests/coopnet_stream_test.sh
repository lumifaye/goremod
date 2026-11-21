set -eu
cd "$(dirname "$0")/../.."
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
common=WiiU/third_party/coopnet/common
c++ -std=gnu++17 -I"$common" -IWiiU/third_party/coopnet/lib/include \
    fork/tests/coopnet_stream_test.cpp "$common"/*.cpp PC/lib/coopnet/linux/libjuice.a -pthread -o "$tmp/test"
"$tmp/test"
