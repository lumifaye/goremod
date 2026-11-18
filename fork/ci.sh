set -u
name="$1"
shift
log="${RUNNER_TEMP:-/tmp}/ci-$(printf '%s' "$name" | tr -c 'A-Za-z0-9' '-').log"

"$@" > >(tee "$log") 2>&1
status=$?
sleep 1
[ "$status" -eq 0 ] && exit 0

annotate() {
    local title="$1" text
    text=$(cut -c1-300 | sed -e 's/\x1b\[[0-9;]*[A-Za-z]//g' -e 's/%/%25/g' -e 's/\r//g' | awk '{ printf "%s%%0A", $0 }')
    [ -n "$text" ] && echo "::error title=${title}::${text}"
}

grep -n -i -E '(^|[^a-z_])(fatal error|error)[: ]|undefined reference|multiple definition|cannot find|No such file|No rule to make|FAILED|Exception|What went wrong|not found' "$log" \
    | grep -v -E 'Werror|-Wno-error|warning:' | head -40 | annotate "$name: errors"
tail -n 40 "$log" | annotate "$name: last lines"
exit "$status"
