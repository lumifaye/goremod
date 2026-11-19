#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include <time.h>
#include <xsdk/kernel.h>
#include "controller_xbox360.h"
extern int32_t osContInit(void *, uint8_t *, void *);
extern void osContGetReadData(OSContPad *);
bool configDisableGamepads;
unsigned int configRumbleStrength;
unsigned int configGamepadNumber;
static INPUT_STATE mock[4];
static bool present[4];
static int calls;
static int rumble_calls;
static uint32_t rumble_user;
static INPUT_VIBRATION last_vibration;
static uint32_t rumble_status;

uint32_t XamInputGetState(uint32_t user, uint32_t flags, INPUT_STATE *out) {
    assert(flags == 0 && user < 4); ++calls;
    if (!present[user]) return 1167;
    *out = mock[user]; return 0;
}
uint32_t XamInputSetState(uint32_t user, uint32_t flags, const INPUT_VIBRATION *vibration) {
    assert(flags == 0 && user < 4 && vibration);
    ++rumble_calls;
    rumble_user = user;
    last_vibration = *vibration;
    return rumble_status;
}

int main(void) {
    OSContPad p = {0};
    controller_xbox360.init();
    mock[0].gamepad.buttons = INPUT_GAMEPAD_A | INPUT_GAMEPAD_B | INPUT_GAMEPAD_START | INPUT_GAMEPAD_DPAD_UP | INPUT_GAMEPAD_LEFT_SHOULDER;
    mock[0].gamepad.thumb_lx = INT16_MIN; mock[0].gamepad.thumb_ly = INT16_MAX;
    mock[0].gamepad.thumb_rx = INT16_MAX; mock[0].gamepad.thumb_ry = INT16_MIN;
    present[0] = true; controller_xbox360.read(&p);
    assert((p.button & (A_BUTTON|B_BUTTON|START_BUTTON|U_JPAD|Z_TRIG|R_CBUTTONS|D_CBUTTONS)) ==
           (A_BUTTON|B_BUTTON|START_BUTTON|U_JPAD|Z_TRIG|R_CBUTTONS|D_CBUTTONS));
    assert(p.stick_x == -80 && p.stick_y == 80 && p.ext_stick_x == 80 && p.ext_stick_y == -80);
    memset(&p, 0, sizeof(p)); memset(&mock[0], 0, sizeof(mock[0]));
    mock[0].gamepad.thumb_lx = 6000; mock[0].gamepad.left_trigger = 30;
    controller_xbox360.read(&p); assert(p.stick_x == 0 && !(p.button & Z_TRIG));
    mock[0].gamepad.thumb_lx = -6000;
    controller_xbox360.read(&p); assert(p.stick_x == 0);
    mock[0].gamepad.left_trigger = 31; mock[0].gamepad.right_trigger = 31;
    controller_xbox360.read(&p); assert((p.button & (Z_TRIG|R_TRIG)) == (Z_TRIG|R_TRIG));
    configDisableGamepads = true; calls = 0; memset(&p, 0, sizeof(p)); controller_xbox360.read(&p);
    assert(calls == 0 && p.button == 0 && rumble_calls == 0); configDisableGamepads = false;
    present[0] = false; present[2] = true; mock[2].gamepad.buttons = INPUT_GAMEPAD_BACK;
    configGamepadNumber = 9; controller_xbox360.read(&p); assert(p.button & L_TRIG);
    assert(controller_xbox360.rawkey() == VK_INVALID);

    int previous_rumble_calls = rumble_calls;
    controller_xbox360.rumble_play(0.5f, 10.0f);
    assert(rumble_calls == previous_rumble_calls + 1 && rumble_user == 2);
    assert(last_vibration.left_motor_speed == 32768 && last_vibration.right_motor_speed == 32768);
    controller_xbox360.rumble_play(1.5f, 10.0f);
    assert(last_vibration.left_motor_speed == UINT16_MAX && last_vibration.right_motor_speed == UINT16_MAX);
    controller_xbox360.rumble_stop();
    assert(last_vibration.left_motor_speed == 0 && last_vibration.right_motor_speed == 0);

    controller_xbox360.rumble_play(0.5f, 0.01f);
    const struct timespec pause = { 0, 30000000L };
    (void)nanosleep(&pause, NULL);
    previous_rumble_calls = rumble_calls;
    memset(&p, 0, sizeof(p)); controller_xbox360.read(&p);
    assert(rumble_calls == previous_rumble_calls + 1);
    assert(last_vibration.left_motor_speed == 0 && last_vibration.right_motor_speed == 0);

    uint8_t bits = 0; assert(osContInit(0, &bits, 0) == 0 && bits == 1);
    present[2] = true; mock[2].gamepad.buttons = INPUT_GAMEPAD_A; configGamepadNumber = 2;
    memset(&p, 0, sizeof(p)); osContGetReadData(&p); assert(p.button & A_BUTTON);
    controller_shutdown();
}
