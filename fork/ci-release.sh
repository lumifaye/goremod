set -eu
folder="$1"
tag="build-$GITHUB_RUN_NUMBER"
commit="${GITHUB_SHA:0:7}"
notes="$(mktemp)"

all="Realism64-Windows.zip|Windows|Windows, flat screen. Unpack it and start \`sm64coopdx.exe\`.
Realism64-Linux.zip|Linux|Linux (64-bit Intel or AMD), flat screen. Unpack it and start \`sm64coopdx\`; it uses SDL2 from your system, see the \`README.txt\` in it.
Realism64-macOS-AppleSilicon.zip|Mac (Apple silicon)|Macs with an Apple processor (M1 and later), macOS 11 or later. See below for the first start.
Realism64-macOS-Intel.zip|Mac (Intel)|Macs with an Intel processor, macOS 11 or later. See below for the first start.
Realism64-VR-Windows.zip|Windows VR|Windows with a PC VR headset. Unpack it and start \`SM64-Co-Op-DX-VR.exe\`.
Realism64-Android.apk|Android|Android phones and tablets.
Realism64-VR-Quest.apk|Quest|Meta Quest headsets, installed from a computer (SideQuest or adb)."

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
    echo "SM64 Coop DX with GORE / Hard-Mode built in. This build is from commit [\`$commit\`]($GITHUB_SERVER_URL/$GITHUB_REPOSITORY/commit/$GITHUB_SHA) of \`$GITHUB_REF_NAME\` ([the run]($GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID))."
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
        echo "**On Mac:** the app isn't signed by an Apple-recognized developer, so macOS may block it at first. Unzip it, try to open \`Realism64.app\` once, then allow it in System Settings > Privacy & Security (\"Open Anyway\"); on older systems right-click the app and choose Open. Or, in Terminal: \`xattr -dr com.apple.quarantine Realism64.app\`."
        echo
    fi
    echo "You need your own Super Mario 64 US ROM. The game will ask for it the first time you start it; no ROM is included."
} > "$notes"

if gh release view "$tag" > /dev/null 2>&1; then
    gh release upload "$tag" "${files[@]}" --clobber
    gh release edit "$tag" --title "$title" --notes-file "$notes" $latest
else
    gh release create "$tag" "${files[@]}" --target "$GITHUB_SHA" --title "$title" --notes-file "$notes" $latest
fi

echo "::notice title=Release::$title: $GITHUB_SERVER_URL/$GITHUB_REPOSITORY/releases/tag/$tag"
