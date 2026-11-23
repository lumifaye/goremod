set -eu
folder="$1"
file="$folder/Realism64-macOS-Intel.zip"
tag="build-$GITHUB_RUN_NUMBER-macos-intel"
title="Realism64 build $GITHUB_RUN_NUMBER (macOS Intel)"
notes="$(mktemp)"
[ -s "$file" ] || { echo '::error title=Intel release::Intel artifact is missing'; exit 1; }
{
    echo "Intel Mac build of Realism64 | [commit \`${GITHUB_SHA:0:7}\`]($GITHUB_SERVER_URL/$GITHUB_REPOSITORY/commit/$GITHUB_SHA)"
    echo
    echo "Intel Mac, macOS 10.15 or newer. If it won't open, allow it in System Settings > Privacy & Security or run \`xattr -dr com.apple.quarantine Realism64.app\`."
    echo
    echo "Other platforms: $GITHUB_SERVER_URL/$GITHUB_REPOSITORY/releases/tag/build-$GITHUB_RUN_NUMBER"
    echo
    echo "You need your own Super Mario 64 US ROM; it isn't included."
} > "$notes"
if gh release view "$tag" > /dev/null 2>&1; then
    gh release upload "$tag" "$file" --clobber
    gh release edit "$tag" --title "$title" --notes-file "$notes" --prerelease --latest=false
else
    gh release create "$tag" "$file" --target "$GITHUB_SHA" --title "$title" --notes-file "$notes" --prerelease --latest=false
fi
echo "::notice title=Intel release::$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/releases/tag/$tag"
