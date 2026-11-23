#!/usr/bin/env python3
"""Run each platform's actual animation sampler against truncated/custom skeletons."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
harness = r'''
#include <stdint.h>
#include <stddef.h>
#include <assert.h>
#include <stdio.h>
typedef int16_t s16; typedef int32_t s32; typedef uint16_t u16; typedef uint32_t u32;
struct Animation { u16 *values, *index; u32 valuesLength, indexLength; };
FUNCTION
int main(void) {
    u16 values[] = { 11, 22, 33 };
    u16 indices[] = { 2, 0, 1, 3, 0, 0 };
    struct Animation a = { values, indices, 3, 6 };
    u16 *p = indices;
    assert(retrieve_animation_value(&a, 1, &p) == 22);
    assert(retrieve_animation_value(&a, 0, &p) == 33); /* index == length */
    assert(retrieve_animation_value(&a, 0, &p) == 0); /* empty channel */
    assert(retrieve_animation_value(&a, 0, &p) == 0); /* extra model bone */
    assert(retrieve_animation_value(&a, 100, &p) == 0);
    p = indices; assert(retrieve_animation_value(&a, -2, &p) == 11);
    a.valuesLength = 0; p = indices; assert(retrieve_animation_value(&a, 0, &p) == 0);
    a.indexLength = 0; assert(retrieve_animation_value(&a, 0, &p) == 0);
    assert(retrieve_animation_value(NULL, 0, &p) == 0);
    puts("animation bounds ok");
}
'''
with tempfile.TemporaryDirectory() as tmp:
    for platform in ('PC', 'VR', 'Android', 'WiiU'):
        source = (root / platform / 'src/engine/graph_node.c').read_text()
        start = source.index('s16 retrieve_animation_value(')
        end = source.index('\n}', start) + 2
        test = Path(tmp) / 'test.c'
        test.write_text(harness.replace('FUNCTION', source[start:end]))
        exe = Path(tmp) / 'test'
        subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-fsanitize=undefined', str(test), '-o', str(exe)], check=True)
        subprocess.run([str(exe)], check=True)
        print(platform, 'passed', flush=True)
