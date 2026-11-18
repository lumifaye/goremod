set -eu
folder="$1"
tag="wiiu-$GITHUB_RUN_NUMBER"
commit="${GITHUB_SHA:0:7}"
notes="$(mktemp)"

all="Realism64-WiiU.zip|Realism64|my realism version
SM64CoopDX-WiiU.zip|SM64 CoopDX|SM64 Coop DX without my changes
Realism64-WiiU.rpx|Realism64 (.rpx)|just the program, use the zip for the full package
SM64CoopDX-WiiU.rpx|SM64 CoopDX (.rpx)|just the program, use the zip for the full package"

files=()
have=""
while IFS='|' read -r file short use; do
    if [ -s "$folder/$file" ]; then
        files+=("$folder/$file")
        case "$file" in *.zip) have="${have:+$have, }$short";; esac
    fi
done <<< "$all"

if [ ${#files[@]} -eq 0 ] || [ -z "$have" ]; then
    echo "::error title=Wii U release::nothing was built, so there is nothing to release"
    exit 1
fi

title="Wii U test build $GITHUB_RUN_NUMBER ($have) - console testing is limited"

{
    echo "**wii u test build:** console testing is limited so it might not work | [commit \`$commit\`]($GITHUB_SERVER_URL/$GITHUB_REPOSITORY/commit/$GITHUB_SHA)."
    echo
    echo "Realism64 is my version, SM64 Coop DX is the port without my realism changes. use the zip for the full game"
    echo
    echo "unzip onto your Aroma SD card and put your own Super Mario 64 US ROM at \`wiiu/apps/sm64coopdx/roms/baserom.us.z64\` (no ROM is included)"
    echo
    echo "mod sounds and voice chat haven't been tested on a console. CoopNet (AGPL v3) and libjuice (MPL 2.0) source and licenses: \`WiiU/third_party\`"
} > "$notes"

if gh release view "$tag" > /dev/null 2>&1; then
    gh release upload "$tag" "${files[@]}" --clobber
    gh release edit "$tag" --title "$title" --notes-file "$notes" --prerelease --latest=false
else
    gh release create "$tag" "${files[@]}" --target "$GITHUB_SHA" --title "$title" --notes-file "$notes" --prerelease --latest=false
fi

echo "::notice title=Wii U release::$title: $GITHUB_SERVER_URL/$GITHUB_REPOSITORY/releases/tag/$tag"
