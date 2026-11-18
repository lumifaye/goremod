set -eu
folder="$1"
tag="wiiu-$GITHUB_RUN_NUMBER"
commit="${GITHUB_SHA:0:7}"
notes="$(mktemp)"

all="Realism64-WiiU.zip|Realism64|SM64 Coop DX with GORE / Hard-Mode built in, like the PC build (same mods and lobby list).
SM64CoopDX-WiiU.zip|SM64 CoopDX|The Wii U port of SM64 Coop DX v1.5.1 without this project's changes.
Realism64-WiiU.rpx|Realism64 (.rpx)|Just the program, without the files in the zip. You don't need this if you have the zip.
SM64CoopDX-WiiU.rpx|SM64 CoopDX (.rpx)|Just the program, without the files in the zip. You don't need this if you have the zip."

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
    echo "**This is a test build. Wii U console testing is limited, so it might not work.** It was compiled with devkitPPC and wut from commit [\`$commit\`]($GITHUB_SERVER_URL/$GITHUB_REPOSITORY/commit/$GITHUB_SHA) of \`$GITHUB_REF_NAME\`."
    echo
    echo "| File | What it is |"
    echo "|---|---|"
    printf '%s' "$table"
    echo
    echo "For a Wii U with Aroma: unzip it onto the SD card, merging the zip's \`wiiu\` folder with the card's \`wiiu\` folder. Put your own Super Mario 64 US ROM at \`wiiu/apps/sm64coopdx/roms/baserom.us.z64\`. No ROM is included. The readme in the zip has the rest."
    echo
    echo "Mod sounds and voice chat have Wii U code, but they have not been tested on a console. CoopNet (GNU AGPL v3) and libjuice (MPL 2.0) are compiled in; their source with the Wii U changes is in this repository under \`WiiU/third_party\`."
} > "$notes"

if gh release view "$tag" > /dev/null 2>&1; then
    gh release upload "$tag" "${files[@]}" --clobber
    gh release edit "$tag" --title "$title" --notes-file "$notes" --prerelease --latest=false
else
    gh release create "$tag" "${files[@]}" --target "$GITHUB_SHA" --title "$title" --notes-file "$notes" --prerelease --latest=false
fi

echo "::notice title=Wii U release::$title: $GITHUB_SERVER_URL/$GITHUB_REPOSITORY/releases/tag/$tag"
