set -eu
folder="$1"
tag="wiiu-$GITHUB_RUN_NUMBER"
commit="${GITHUB_SHA:0:7}"
notes="$(mktemp)"

all="Realism64-WiiU.zip|Realism64|My realism-focused version.
SM64CoopDX-WiiU.zip|SM64 CoopDX|SM64 Coop DX without this project's changes.
Realism64-WiiU.rpx|Realism64 (.rpx)|Program only; use the zip for the full package.
SM64CoopDX-WiiU.rpx|SM64 CoopDX (.rpx)|Program only; use the zip for the full package."

files=()
have=""
table=""
while IFS='|' read -r file short use; do
    if [ -s "$folder/$file" ]; then
        files+=("$folder/$file")
        case "$file" in *.zip) have="${have:+$have, }$short";; esac
        table="$table| \`$file\` | $use |"$'\n'
    fi
done <<< "$all"

if [ ${#files[@]} -eq 0 ] || [ -z "$have" ]; then
    echo "::error title=Wii U release::nothing was built, so there is nothing to release"
    exit 1
fi

title="Wii U test build $GITHUB_RUN_NUMBER ($have) - console testing is limited"

{
    echo "**Wii U test build:** console testing is limited, so it might not work. [Commit \`$commit\`]($GITHUB_SERVER_URL/$GITHUB_REPOSITORY/commit/$GITHUB_SHA)."
    echo
    echo "| File | What it is |"
    echo "|---|---|"
    printf '%s' "$table"
    echo
    echo "For Aroma: unzip onto your SD card and merge the \`wiiu\` folders. Put your own Super Mario 64 US ROM at \`wiiu/apps/sm64coopdx/roms/baserom.us.z64\`. No ROM is included."
    echo
    echo "Mod sounds and voice chat haven't been tested on a console. Includes CoopNet (AGPL v3) and libjuice (MPL 2.0); source and licenses are in \`WiiU/third_party\`."
} > "$notes"

if gh release view "$tag" > /dev/null 2>&1; then
    gh release upload "$tag" "${files[@]}" --clobber
    gh release edit "$tag" --title "$title" --notes-file "$notes" --prerelease --latest=false
else
    gh release create "$tag" "${files[@]}" --target "$GITHUB_SHA" --title "$title" --notes-file "$notes" --prerelease --latest=false
fi

echo "::notice title=Wii U release::$title: $GITHUB_SERVER_URL/$GITHUB_REPOSITORY/releases/tag/$tag"
