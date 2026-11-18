set -eu
program="$1"
folder="$2"
shift 2
from=/mingw64/bin
copied=""
licences=""

needs() {
    objdump -p "$1" | awk '/DLL Name:/ { print $3 }'
}

one() {
    local dll="$1" package
    [ -f "$folder/$dll" ] && return 0
    cp "$from/$dll" "$folder/"
    copied="$copied $dll"
    package=$(pacman -Qqo "$from/$dll" 2>/dev/null | sed 's/^mingw-w64-x86_64-//' || true)
    if [ -n "$package" ] && [ -d "/mingw64/share/licenses/$package" ] && [ ! -d "$folder/licenses/$package" ]; then
        mkdir -p "$folder/licenses/$package"
        cp -r "/mingw64/share/licenses/$package/." "$folder/licenses/$package/"
        licences="$licences $package"
    fi
    take "$from/$dll"
}

take() {
    local dll
    for dll in $(needs "$1"); do
        [ -f "$from/$dll" ] || continue
        one "$dll"
    done
}

take "$program"
for dll in "$@"; do
    if [ ! -f "$from/$dll" ]; then
        echo "::error title=DLLs::$dll is not in $from"
        exit 1
    fi
    one "$dll"
done

case "$copied" in
    *libgcc*|*libstdc++*)
        case " $licences " in
            *" gcc-libs "*) ;;
            *)
                for text in GPL-3.0-or-later.txt GCC-exception-3.1.txt; do
                    if [ -f "/usr/share/licenses/spdx/$text" ]; then
                        mkdir -p "$folder/licenses/gcc-libs"
                        cp "/usr/share/licenses/spdx/$text" "$folder/licenses/gcc-libs/"
                        licences="$licences gcc-libs:$text"
                    fi
                done
                ;;
        esac
        ;;
esac

echo "::notice title=DLLs packed with $(basename "$program")::${copied:- none (it needs only what Windows has)} | licences:${licences:- none}"
