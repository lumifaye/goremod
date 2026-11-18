#!/usr/bin/env bash
set -eu
folder="$1"
tag="wiiu-$GITHUB_RUN_NUMBER"
commit="${GITHUB_SHA:0:7}"
notes="$(mktemp)"

all="Realism64-WiiU.zip|Realism64|The game with GORE / Hard-Mode built in, as on the PC (same mods, same list of lobbies).
SM64CoopDX-WiiU.zip|SM64 CoopDX|The Wii U port of SM64 Coop DX v1.5.1 as it is, with nothing of this project in it.
Realism64-WiiU.rpx|Realism64 (.rpx)|The program alone, without the files packed with it. Not needed with the zip.
SM64CoopDX-WiiU.rpx|SM64 CoopDX (.rpx)|The program alone, without the files packed with it. Not needed with the zip."

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
    echo "::error title=Wii U release::nothing was built, there is nothing to release"
    exit 1
fi

title="Wii U test build $GITHUB_RUN_NUMBER ($have) - not tried on a console"

{
    echo "**Nobody has started this on a Wii U yet.** It was compiled with the real Wii U compiler (devkitPPC, wut) from commit [\`$commit\`]($GITHUB_SERVER_URL/$GITHUB_REPOSITORY/commit/$GITHUB_SHA) of \`$GITHUB_REF_NAME\`, and that is all that is known about it."
    echo
    echo "| File | What it is |"
    echo "|---|---|"
    printf '%s' "$table"
    echo
    echo "For a Wii U with homebrew (Aroma): unpack a zip onto the SD card, so that its folder \`wiiu\` goes into the card's \`wiiu\`. Then put your own Super Mario 64 ROM (US version) at \`wiiu/apps/sm64coopdx/roms/baserom.us.z64\`. None is included. The text file in the zip says the rest."
    echo
    echo "Sounds that a mod brings itself are not played on the Wii U, and there is no voice chat. CoopNet (GNU AGPL v3) and libjuice (MPL 2.0) are compiled in; their source with the Wii U changes is in this repository under \`WiiU/third_party\`."
} > "$notes"

if gh release view "$tag" > /dev/null 2>&1; then
    gh release upload "$tag" "${files[@]}" --clobber
    gh release edit "$tag" --title "$title" --notes-file "$notes" --prerelease --latest=false
else
    gh release create "$tag" "${files[@]}" --target "$GITHUB_SHA" --title "$title" --notes-file "$notes" --prerelease --latest=false
fi

echo "::notice title=Wii U release::$title: $GITHUB_SERVER_URL/$GITHUB_REPOSITORY/releases/tag/$tag"
