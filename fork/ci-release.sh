set -eu
folder="$1"
tag="build-$GITHUB_RUN_NUMBER"
commit="${GITHUB_SHA:0:7}"
notes="$(mktemp)"

all="Realism64-Windows-VR-and-Flatscreen.zip|Windows (flat + VR)|windows: unzip and run \`sm64coopdx.exe\` for flat screen or enable VR Mode in settings.
Realism64-Linux.zip|Linux|linux (64-bit): unzip and run \`sm64coopdx\`. see the included README for dependencies
Realism64-macOS-AppleSilicon.zip|Mac (Apple silicon)|apple silicon mac, macOS 11+
Realism64-macOS-Intel.zip|Mac (Intel)|intel mac, macOS 11+
Realism64-Android.apk|Android|android phones and tablets
Realism64-VR-Quest.apk|Quest|quest: install with SideQuest or adb
Realism64-WiiU.zip|Wii U|wii u: my realism version
SM64CoopDX-WiiU.zip|Wii U (stock)|wii u: the port without my changes"

files=()
have=""
missing=""
while IFS='|' read -r file short use; do
    if [ -s "$folder/$file" ]; then
        files+=("$folder/$file")
        have="${have:+$have, }$short"
    else
        missing="${missing:+$missing, }$short"
    fi
done <<< "$all"

for file in Realism64-WiiU.rpx SM64CoopDX-WiiU.rpx; do
    if [ -s "$folder/$file" ]; then files+=("$folder/$file"); fi
done

if [ ${#files[@]} -eq 0 ]; then
    echo "::error title=Release::nothing was built, so there is nothing to release"
    exit 1
fi

title="Realism64 build $GITHUB_RUN_NUMBER"
if [ -n "$missing" ]; then
    title="$title ($have only)"
fi

{
    echo "my realism version of SM64 Coop DX | [commit \`$commit\`]($GITHUB_SERVER_URL/$GITHUB_REPOSITORY/commit/$GITHUB_SHA)"
    echo
    if [ -n "$missing" ]; then
        echo "not in this build: $missing"
        echo
    fi
    if printf '%s' "$have" | grep -q "Mac"; then
        echo "mac: if it won't open allow it in System Settings > Privacy & Security or run \`xattr -dr com.apple.quarantine Realism64.app\`"
        echo
    fi
    if [ -s "$folder/Realism64-WiiU.zip" ] || [ -s "$folder/SM64CoopDX-WiiU.zip" ]; then
        echo "wii u: console testing is limited. unzip to your Aroma SD card and put your ROM at \`wiiu/apps/sm64coopdx/roms/baserom.us.z64\`"
        echo "Realism64 is my version; SM64 Coop DX is the port without my realism changes. sound and voice chat haven't been tested on a console"
        echo
    fi
    echo "you need your own Super Mario 64 US ROM, it isn't included"
} > "$notes"

if gh release view "$tag" > /dev/null 2>&1; then
    gh release upload "$tag" "${files[@]}" --clobber
    gh release edit "$tag" --title "$title" --notes-file "$notes" --prerelease --latest=false
else
    gh release create "$tag" "${files[@]}" --target "$GITHUB_SHA" --title "$title" --notes-file "$notes" --prerelease --latest=false
fi

echo "::notice title=Release::$title: $GITHUB_SERVER_URL/$GITHUB_REPOSITORY/releases/tag/$tag"
