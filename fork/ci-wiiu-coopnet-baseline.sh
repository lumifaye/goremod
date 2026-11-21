#!/usr/bin/env bash
# Keep the transport that restored outgoing joins. Never overwrite the staged
# game adapter: it owns current host routing, mod negotiation and lobby names.
set -euo pipefail
baseline=fdfff4b17e812e6caa2724ce82bbcb4b796452c5
if ! git cat-file -e "$baseline^{commit}" 2>/dev/null; then
    git fetch --no-tags --depth=1 origin "$baseline"
fi
git archive "$baseline" WiiU/third_party/coopnet WiiU/third_party/libjuice | tar -x
