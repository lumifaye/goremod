#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
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
uint32_t XamInputGetState(uint32_t user, uint32_t flags, INPUT_STATE *out) {
    assert(flags == 0 && user < 4); ++calls;
    if (!present[user]) return 1167;
    *out = mock[user]; return 0;
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
    mock[0].gamepad.thumb_lx=5999; mock[0].gamepad.left_trigger=30;
    controller_xbox360.read(&p); assert(p.stick_x==0 && !(p.button & Z_TRIG));
    mock[0].gamepad.left_trigger=31; mock[0].gamepad.right_trigger=31;
    controller_xbox360.read(&p); assert((p.button & (Z_TRIG|R_TRIG))==(Z_TRIG|R_TRIG));
    configDisableGamepads=true; calls=0; memset(&p,0,sizeof(p)); controller_xbox360.read(&p);
    assert(calls==0 && p.button==0); configDisableGamepads=false;
    present[0]=false; present[2]=true; mock[2].gamepad.buttons=INPUT_GAMEPAD_BACK;
    configGamepadNumber=9; controller_xbox360.read(&p); assert(p.button & L_TRIG);
    memset(&p,0,sizeof(p)); present[2]=false; controller_xbox360.read(&p); assert(p.button==0);
    assert(controller_xbox360.rawkey()==VK_INVALID);
    uint8_t bits=0; assert(osContInit(0,&bits,0)==0 && bits==1);
    present[2]=true; mock[2].gamepad.buttons=INPUT_GAMEPAD_A; configGamepadNumber=2;
    memset(&p,0,sizeof(p)); osContGetReadData(&p); assert(p.button & A_BUTTON);
    controller_shutdown();
}
