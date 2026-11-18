set -eu
folder="$1"
tag="build-$GITHUB_RUN_NUMBER"
commit="${GITHUB_SHA:0:7}"
notes="$(mktemp)"

all="Realism64-Windows.zip|Windows|Windows: unzip and run \`sm64coopdx.exe\`.
Realism64-Linux.zip|Linux|Linux (64-bit): unzip and run \`sm64coopdx\`. See the included README for dependencies.
Realism64-macOS-AppleSilicon.zip|Mac (Apple silicon)|Apple silicon Mac, macOS 11+.
Realism64-macOS-Intel.zip|Mac (Intel)|Intel Mac, macOS 11+.
Realism64-VR-Windows.zip|Windows VR|Windows VR: unzip and run \`SM64-Co-Op-DX-VR.exe\`.
Realism64-Android.apk|Android|Android phones and tablets.
Realism64-VR-Quest.apk|Quest|Quest: install with SideQuest or adb."

files=()
have=""
missing=""
table=""
while IFS='|' read -r file short use; do
    if [ -s "$folder/$file" ]; then
        files+=("$folder/$file")
        have="${have:+$have, }$short"
        table="$table| \`$file\` | $use |"$'\n'
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
    echo "My realism-focused version of SM64 Coop DX. [Commit \`$commit\`]($GITHUB_SERVER_URL/$GITHUB_REPOSITORY/commit/$GITHUB_SHA) | [Build run]($GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID)"
    echo
    echo "| File | For |"
    echo "|---|---|"
    printf '%s' "$table"
    echo
    if [ -n "$missing" ]; then
        echo "Missing from this build: $missing."
        echo
    fi
    if printf '%s' "$have" | grep -q "Mac"; then
        echo "**Mac:** if the unsigned app is blocked, allow it in System Settings > Privacy & Security or run \`xattr -dr com.apple.quarantine Realism64.app\`."
        echo
    fi
    echo "You need your own Super Mario 64 US ROM. No ROM is included."
} > "$notes"

if gh release view "$tag" > /dev/null 2>&1; then
    gh release upload "$tag" "${files[@]}" --clobber
    gh release edit "$tag" --title "$title" --notes-file "$notes" $latest
else
    gh release create "$tag" "${files[@]}" --target "$GITHUB_SHA" --title "$title" --notes-file "$notes" $latest
fi

echo "::notice title=Release::$title: $GITHUB_SERVER_URL/$GITHUB_REPOSITORY/releases/tag/$tag"
