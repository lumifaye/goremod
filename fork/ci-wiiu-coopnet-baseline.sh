#!/usr/bin/env bash
# Controlled comparison: stage only CoopNet and its ICE backend from the
# revision reported working on hardware. Do not reset the game or its mods.
set -euo pipefail
baseline=fdfff4b17e812e6caa2724ce82bbcb4b796452c5
if ! git cat-file -e "$baseline^{commit}" 2>/dev/null; then
    git fetch --no-tags --depth=1 origin "$baseline"
fi
git archive "$baseline" WiiU/src/pc/network/coopnet WiiU/third_party/coopnet WiiU/third_party/libjuice | tar -x
# fork/apply.py already set the build's version. Its lobby namespace must
# still match the Realism64 PC host, not the stock game's public lobby list.
python3 - <<'PY'
from pathlib import Path
p = Path('WiiU/src/pc/network/coopnet/coopnet.c')
s = p.read_text()
assert s.count('GAME_NAME,') == 3
p.write_text(s.replace('GAME_NAME,', 'FORK_COOPNET_GAME,'))
PY
