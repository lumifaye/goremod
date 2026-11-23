#!/usr/bin/env python3
from pathlib import Path
source = (Path(__file__).resolve().parents[2] / 'Android/src/pc/gfx/gfx_experimental_post.h').read_text()
assert 'precision highp float;' in source
assert source.count('varying highp vec2 uv;') == 2
print('Android experimental post processing UV precision: ok')
