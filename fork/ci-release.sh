set -eu
folder="$1"
tag="build-$GITHUB_RUN_NUMBER"
commit="${GITHUB_SHA:0:7}"
notes="$(mktemp)"

all="Realism64-Windows.zip|Windows|windows: unzip and run \`sm64coopdx.exe\`.
Realism64-Linux.zip|Linux|linux (64-bit): unzip and run \`sm64coopdx\`. see the included README for dependencies
Realism64-macOS-AppleSilicon.zip|Mac (Apple silicon)|apple silicon mac, macOS 11+
Realism64-macOS-Intel.zip|Mac (Intel)|intel mac, macOS 11+
Realism64-VR-Windows.zip|Windows VR|windows vr: unzip and run \`SM64-Co-Op-DX-VR.exe\`.
Realism64-Android.apk|Android|android phones and tablets
Realism64-VR-Quest.apk|Quest|quest: install with SideQuest or adb"

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

if [ ${#files[@]} -eq 0 ]; then
    echo "::error title=Release::nothing was built, so there is nothing to release"
    exit 1
fi

title="Realism64 build $GITHUB_RUN_NUMBER"
latest="--latest"
if [ -n "$missing" ]; then
    title="$title ($have only)"
    latest="--latest=false"
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
    echo "you need your own Super Mario 64 US ROM, it isn't included"
} > "$notes"

if gh release view "$tag" > /dev/null 2>&1; then
    gh release upload "$tag" "${files[@]}" --clobber
    gh release edit "$tag" --title "$title" --notes-file "$notes" $latest
else
    gh release create "$tag" "${files[@]}" --target "$GITHUB_SHA" --title "$title" --notes-file "$notes" $latest
fi

echo "::notice title=Release::$title: $GITHUB_SERVER_URL/$GITHUB_REPOSITORY/releases/tag/$tag"
