import os
import subprocess
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[2]
controller = (root / 'WiiU/src/pc/controller/controller_wiiu.c').read_text()
a = controller.index('static bool s_touch_down = false;')
b = controller.index('\nenum WiiUDebugSource', a)
touch = controller[a:b]
read_start = controller.index('static void controller_wiiu_read(OSContPad* pad) {')
read_end = controller.index('static u32 controller_wiiu_rawkey', read_start)
assert controller[read_start:read_end].count('controller_wiiu_try_vpad_input(') == 1
prelude = '''#include <stdbool.h>
#include <stddef.h>
#include <assert.h>
#include <math.h>
static bool panel_active = false, gDjuiChatBoxFocus = false, gDjuiConsoleFocus = false, keyboard_active = false;
static bool djui_panel_is_active(void) { return panel_active; }
static bool wiiu_keyboard_active(void) { return keyboard_active; }
#define VPAD_CHAN_0 0
#define VPAD_TP_854X480 2
#define VPAD_VALID 0
typedef struct { unsigned short x,y,touched,validity; } VPADTouchData;
typedef struct { VPADTouchData tpNormal; } VPADStatus;
void VPADGetTPCalibratedPointEx(int chan, int res, VPADTouchData *dst, const VPADTouchData *src) {
    assert(chan == 0 && res == 2);
    *dst = *src;
}
'''
checks = '''
int main(void) {
    VPADStatus s = {0}; float x = 0, y = 0;
    s.tpNormal.touched = 1; s.tpNormal.x = 427; s.tpNormal.y = 240;
    controller_wiiu_touch_sample(&s);
    assert(controller_wiiu_touch_pressed(&x, &y) && x == 0.5f && y == 0.5f);
    controller_wiiu_touch_sample(&s);
    assert(!controller_wiiu_touch_pressed(&x, &y));
    s.tpNormal.touched = 0; controller_wiiu_touch_sample(&s);
    s.tpNormal.touched = 1; s.tpNormal.validity = 1; controller_wiiu_touch_sample(&s);
    assert(!controller_wiiu_touch_pressed(&x, &y));
    s.tpNormal.validity = 0; controller_wiiu_touch_sample(&s);
    assert(controller_wiiu_touch_pressed(&x, &y));
    assert(!controller_wiiu_touch_pressed(&x, &y));
    assert(controller_wiiu_touch_state(&x, &y) && x == 0.5f && y == 0.5f);
    s.tpNormal.x = 854; s.tpNormal.y = 480; controller_wiiu_touch_sample(&s);
    assert(controller_wiiu_touch_state(&x, &y) && x == 1.0f && y == 1.0f);
    s.tpNormal.touched = 0; controller_wiiu_touch_sample(&s);
    assert(!controller_wiiu_touch_state(NULL, NULL));
    panel_active = true; s.tpNormal.touched = 1; controller_wiiu_touch_sample(&s);
    assert(!controller_wiiu_touch_pressed(&x, &y));
    panel_active = false; assert(!controller_wiiu_touch_pressed(&x, &y));
    s.tpNormal.touched = 0; controller_wiiu_touch_sample(&s);
    keyboard_active = true; s.tpNormal.touched = 1; controller_wiiu_touch_sample(&s);
    assert(!controller_wiiu_touch_pressed(&x, &y));
}
'''
binding_pre = '''#include <assert.h>
#define MAX_PLAYERS 16
typedef struct { int value; int isNil; } lua_State;
int gGorePacketSender = -1;
static void lua_pushnil(lua_State* L) { L->isNil = 1; }
static void lua_pushinteger(lua_State* L, int value) { L->value = value; L->isNil = 0; }
'''
binding_test = '''
int main(void) {
    lua_State L = {0};
    gGorePacketSender = -1; assert(smlua_func_gore_packet_sender(&L) == 1 && L.isNil);
    gGorePacketSender = 0; smlua_func_gore_packet_sender(&L); assert(L.isNil);
    gGorePacketSender = 3; smlua_func_gore_packet_sender(&L); assert(!L.isNil && L.value == 3);
    gGorePacketSender = MAX_PLAYERS; smlua_func_gore_packet_sender(&L); assert(L.isNil);
}
'''

def run_c(text, folder, name):
    source, binary = folder / (name + '.c'), folder / name
    source.write_text(text)
    subprocess.run([os.environ.get('CC', 'cc'), '-std=c11', '-Wall', '-Wextra', '-Werror', str(source), '-o', str(binary), '-lm'], check=True)
    subprocess.run([str(binary)], check=True)

with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    run_c(prelude + touch + checks, tmp, 'touch')
    for port in ('PC', 'VR', 'Android', 'WiiU'):
        custom = (root / port / 'src/pc/network/packets/packet_lua_custom.c').read_text()
        assert 'gGorePacketSender = p->localIndex;\n    smlua_call_event_hooks(HOOK_ON_PACKET_RECEIVE, modIndex, tableIndex);\n    gGorePacketSender = previousGorePacketSender;' in custom
        source = (root / port / 'src/pc/lua/smlua_functions.c').read_text()
        start = source.index('extern int gGorePacketSender;')
        end = source.index('void smlua_bind_functions(void)', start)
        run_c(binding_pre + source[start:end] + binding_test, tmp, port)
print('touch and sender tests passed')
