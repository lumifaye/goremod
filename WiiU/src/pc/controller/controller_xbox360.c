/* Xbox 360 XAM controller backend. Experimental: not yet connected to a game build. */
#if defined(TARGET_XBOX360) && defined(__XSDK__)
#include <stdint.h>
#include <xsdk/kernel.h>
#include "controller_api.h"
#include "../configfile.h"

#define XBOX360_VKBASE 0x3000
#define TRIGGER_THRESHOLD 30
#define RIGHT_STICK_THRESHOLD 16000
#define STICK_DEADZONE 6000

/* XAM uses -32768..32767. Keep endpoints symmetric and leave room for N64's +/-80. */
static int8_t axis_to_n64(int16_t axis) {
    int32_t x = axis;
    if (x > -STICK_DEADZONE && x < STICK_DEADZONE) return 0;
    if (x < -32767) x = -32767;
    return (int8_t)((x * 80) / 32767);
}

static void xbox360_init(void) {}
static void xbox360_reconfig(void) {}
static u32 xbox360_rawkey(void) { return VK_INVALID; }
static void xbox360_shutdown(void) {}

static void xbox360_read(OSContPad *pad) {
    INPUT_STATE state;
    uint32_t user = configGamepadNumber;
    if (configDisableGamepads) return;
    if (user > 3 || XamInputGetState(user, 0, &state) != 0) {
        for (user = 0; user < 4; ++user) {
            if (XamInputGetState(user, 0, &state) == 0) break;
        }
        if (user == 4) return;
    }
    const INPUT_GAMEPAD *p = &state.gamepad;
    uint16_t b = p->buttons;
    if (b & (INPUT_GAMEPAD_A | INPUT_GAMEPAD_Y)) pad->button |= A_BUTTON;
    if (b & (INPUT_GAMEPAD_B | INPUT_GAMEPAD_X)) pad->button |= B_BUTTON;
    if (b & INPUT_GAMEPAD_START) pad->button |= START_BUTTON;
    if ((b & INPUT_GAMEPAD_LEFT_SHOULDER) || p->left_trigger > TRIGGER_THRESHOLD) pad->button |= Z_TRIG;
    if (b & INPUT_GAMEPAD_BACK) pad->button |= L_TRIG;
    if ((b & INPUT_GAMEPAD_RIGHT_SHOULDER) || p->right_trigger > TRIGGER_THRESHOLD) pad->button |= R_TRIG;
    if (b & INPUT_GAMEPAD_DPAD_UP) pad->button |= U_JPAD;
    if (b & INPUT_GAMEPAD_DPAD_DOWN) pad->button |= D_JPAD;
    if (b & INPUT_GAMEPAD_DPAD_LEFT) pad->button |= L_JPAD;
    if (b & INPUT_GAMEPAD_DPAD_RIGHT) pad->button |= R_JPAD;
    if (p->thumb_ry > RIGHT_STICK_THRESHOLD) pad->button |= U_CBUTTONS;
    if (p->thumb_ry < -RIGHT_STICK_THRESHOLD) pad->button |= D_CBUTTONS;
    if (p->thumb_rx < -RIGHT_STICK_THRESHOLD) pad->button |= L_CBUTTONS;
    if (p->thumb_rx > RIGHT_STICK_THRESHOLD) pad->button |= R_CBUTTONS;
    pad->stick_x = axis_to_n64(p->thumb_lx);
    pad->stick_y = axis_to_n64(p->thumb_ly);
    pad->ext_stick_x = axis_to_n64(p->thumb_rx);
    pad->ext_stick_y = axis_to_n64(p->thumb_ry);
}

struct ControllerAPI controller_xbox360 = {
    .vkbase = XBOX360_VKBASE,
    .init = xbox360_init,
    .read = xbox360_read,
    .rawkey = xbox360_rawkey,
    .rumble_play = 0,
    .rumble_stop = 0,
    .reconfig = xbox360_reconfig,
    .shutdown = xbox360_shutdown,
};
#endif
