#!/usr/bin/env bash
# Build target archives (never use the host's sdl2-config or libz).
set -euo pipefail
: "${XSDK_ROOT:?Set XSDK_ROOT to the built SDK}"
if (( $# != 4 )); then echo 'usage: build-deps.sh SDL2_SRC ZLIB_SRC BUILD_DIR PREFIX' >&2; exit 2; fi
sdl=$(realpath "$1"); z=$(realpath "$2"); work=$(realpath -m "$3"); prefix=$(realpath -m "$4")
patchfile=$(realpath "$(dirname "$0")/sdl2-xsdk.patch")
mkdir -p "$work/z" "$prefix/lib" "$prefix/include"
# The upstream configure executes probe binaries. Use the standard zlib
# translation units directly; zconf.h ships in the pinned release.
objects=()
for src in adler32 compress crc32 deflate gzclose gzlib gzread gzwrite infback inffast inflate inftrees trees uncompr zutil; do
    obj="$work/z/$src.o"
    powerpc-xsdk-elf-gcc -O2 -std=gnu17 -DHAVE_UNISTD_H -I"$z" -c "$z/$src.c" -o "$obj"
    objects+=("$obj")
done
powerpc-xsdk-elf-ar rcs "$prefix/lib/libz.a" "${objects[@]}"
install -m644 "$z/zlib.h" "$z/zconf.h" "$prefix/include/"
if ! git -C "$sdl" apply --reverse --check "$patchfile" 2>/dev/null; then
    git -C "$sdl" apply "$patchfile"
fi
cmake -S "$sdl" -B "$work/sdl" -G Ninja \
    -DCMAKE_TOOLCHAIN_FILE="$XSDK_ROOT/cmake/xsdk.cmake" -DCMAKE_INSTALL_PREFIX="$prefix" \
    -DCMAKE_INSTALL_LIBDIR=lib -DCMAKE_C_STANDARD=17 -DCMAKE_BUILD_TYPE=Release \
    -DSDL_SHARED=OFF -DSDL_STATIC=ON -DSDL_TEST=OFF -DSDL_TESTS=OFF -DSDL_PTHREADS=ON \
    -DSDL2_DISABLE_SDL2MAIN=ON -DSDL_HIDAPI=OFF -DSDL_OPENGL=OFF -DSDL_OPENGLES=OFF -DSDL_VULKAN=OFF
cmake --build "$work/sdl" --target install -j"${JOBS:-3}"
test -s "$prefix/lib/libSDL2.a"
