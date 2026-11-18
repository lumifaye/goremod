set -eu
save="$1"
game="$2"
repo="$3"
there="$save/realism64/Gore-Hardmode"

want=$(tr -d ' \r\n' < "$game/fork-embedded-files.txt")
have=$(find "$save/realism64" -type f | wc -l | tr -d ' ')
echo "built-in files the program wrote out: $have (it has $want in it)"
[ "$have" -eq "$want" ]
test -s "$there/main.lua"
test -s "$there/built-in.txt"

count=0
for file in "$repo"/actors/*.bin "$repo"/sound/*.ogg "$repo"/sound/*.m64 "$repo"/levels/*.lvl "$repo"/textures/*.tex; do
    [ -f "$file" ] || continue
    [ "$(cksum < "$file")" = "$(cksum < "$there/${file#"$repo"/}")" ] || { echo "not the same: ${file#"$repo"/}"; exit 1; }
    count=$((count + 1))
done
echo "$count of them compared with this repository: the same"
[ "$count" -gt 100 ]
