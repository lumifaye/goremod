#define _POSIX_C_SOURCE 200809L
/* Xbox 360 XAM controller backend. Experimental: not yet connected to a game build. */
#if defined(TARGET_XBOX360) && defined(__XSDK__)
#include <stdbool.h>
#include <stdint.h>
#include <time.h>
#include <xsdk/kernel.h>
#include "controller_api.h"
#include "../configfile.h"

#define XBOX360_VKBASE 0x3000
#define XBOX360_USER_COUNT 4u
#define TRIGGER_THRESHOLD 30
#define RIGHT_STICK_THRESHOLD 16000
#define STICK_DEADZONE 6000

static uint32_t active_user;
static bool active_user_valid;
static uint32_t rumble_user;
static bool rumble_active;
static uint64_t rumble_deadline_ns;
static bool rumble_deadline_valid;

/* XAM uses -32768..32767. Keep endpoints symmetric and leave room for N64's +/-80. */
static int8_t axis_to_n64(int16_t axis) {
    int32_t x = axis;
    if (x >= -STICK_DEADZONE && x <= STICK_DEADZONE) return 0;
    if (x < -32767) x = -32767;
    return (int8_t)((x * 80) / 32767);
}

static bool xbox360_now_ns(uint64_t *now_ns) {
    struct timespec now;
    if (!now_ns || clock_gettime(CLOCK_MONOTONIC, &now) != 0 || now.tv_sec < 0) return false;
    *now_ns = (uint64_t)now.tv_sec * UINT64_C(1000000000) + (uint64_t)now.tv_nsec;
    return true;
}

static void xbox360_rumble_stop(void) {
    if (rumble_active) {
        const INPUT_VIBRATION stopped = { 0, 0 };
        (void)XamInputSetState(rumble_user, 0, &stopped);
    }
    rumble_active = false;
    rumble_deadline_valid = false;
    rumble_deadline_ns = 0;
}

static void xbox360_update_rumble(void) {
    uint64_t now_ns;
    if (rumble_active && rumble_deadline_valid && xbox360_now_ns(&now_ns) && now_ns >= rumble_deadline_ns)
        xbox360_rumble_stop();
}

static bool xbox360_get_user_state(uint32_t *user_out, INPUT_STATE *state) {
    if (!user_out || !state || configDisableGamepads) return false;

    const uint32_t preferred = configGamepadNumber;
    if (preferred < XBOX360_USER_COUNT && XamInputGetState(preferred, 0, state) == 0) {
        *user_out = preferred;
        return true;
    }

    for (uint32_t user = 0; user < XBOX360_USER_COUNT; ++user) {
        if (user == preferred) continue;
        if (XamInputGetState(user, 0, state) == 0) {
            *user_out = user;
            return true;
        }
    }
    return false;
}

static void xbox360_select_user(uint32_t user) {
    if (active_user_valid && active_user != user) xbox360_rumble_stop();
    active_user = user;
    active_user_valid = true;
}

static void xbox360_rumble_play(float strength, float seconds) {
    INPUT_STATE state;
    uint32_t user;
    uint64_t now_ns;

    if (!(strength > 0.0f) || !(seconds > 0.0f)) {
        xbox360_rumble_stop();
        return;
    }
    if (!xbox360_get_user_state(&user, &state)) {
        xbox360_rumble_stop();
        active_user_valid = false;
        return;
    }

    xbox360_select_user(user);
    if (strength > 1.0f) strength = 1.0f;
    const uint16_t speed = (uint16_t)(strength * 65535.0f + 0.5f);
    const INPUT_VIBRATION vibration = { speed, speed };
    if (XamInputSetState(active_user, 0, &vibration) != 0) {
        xbox360_rumble_stop();
        return;
    }

    rumble_user = active_user;
    rumble_active = true;
    rumble_deadline_valid = false;
    if (xbox360_now_ns(&now_ns)) {
        const double duration_ns = (double)seconds * 1000000000.0;
        const uint64_t remaining_ns = UINT64_MAX - now_ns;
        if (duration_ns >= (double)remaining_ns) {
            rumble_deadline_ns = UINT64_MAX;
        } else {
            rumble_deadline_ns = now_ns + (uint64_t)(duration_ns + 0.5);
        }
        rumble_deadline_valid = true;
    }
}

static void xbox360_init(void) {
    xbox360_rumble_stop();
    active_user = 0;
    active_user_valid = false;
}
static void xbox360_reconfig(void) {}
static u32 xbox360_rawkey(void) { return VK_INVALID; }
static void xbox360_shutdown(void) {
    xbox360_rumble_stop();
    active_user_valid = false;
}

static void xbox360_read(OSContPad *pad) {
    INPUT_STATE state;
    uint32_t user;
    if (!pad) return;

    xbox360_update_rumble();
    if (!xbox360_get_user_state(&user, &state)) {
        active_user_valid = false;
        xbox360_rumble_stop();
        return;
    }
    xbox360_select_user(user);

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
    .rumble_play = xbox360_rumble_play,
    .rumble_stop = xbox360_rumble_stop,
    .reconfig = xbox360_reconfig,
    .shutdown = xbox360_shutdown,
};
#endif
