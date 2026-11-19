#!/usr/bin/env bash
# xSDK writes configure/make output to files, not stdout. Report activity
# without changing its build, its exit status, or the compiler cache key.
set -eu
: "${XSDK_ROOT:?Set XSDK_ROOT to the pinned xSDK checkout}"
export WORK="${WORK:-$HOME/xsdk-gcc-work}"
report() {
    local log
    printf '\n[toolchain %s UTC] ' "$(date -u +%T)"
    df -hP "$HOME" | awk 'NR==2 {print $4 " disk free"}'
    log=$(find "$WORK/logs" -name '*.log' -type f -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -1 | cut -d' ' -f2-)
    if [[ -n $log ]]; then
        stat -c '%n: %s bytes; last write %y' "$log"
        tail -n 2 "$log" | cut -c1-300
    else
        # fetch/unpack happens before the SDK opens its first stage log.
        find "$WORK/src" -maxdepth 1 -type f -printf '%f: %s bytes\n' 2>/dev/null || :
    fi
}
(while sleep 60; do report; done) &
monitor=$!
trap 'kill "$monitor" 2>/dev/null || :; wait "$monitor" 2>/dev/null || :' EXIT
rc=0
bash "$XSDK_ROOT/tools/toolchain/build.sh" || rc=$?
report
exit "$rc"
