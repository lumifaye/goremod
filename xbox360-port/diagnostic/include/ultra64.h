/* Narrow game-interface shim for the diagnostic only, not the real game. */
#ifndef XBOX360_DIAGNOSTIC_ULTRA64_H
#define XBOX360_DIAGNOSTIC_ULTRA64_H
#include <stdint.h>
typedef uint32_t u32;
typedef struct { uint16_t button; int8_t stick_x, stick_y, ext_stick_x, ext_stick_y; uint8_t errnum; } OSContPad;
#define A_BUTTON 0x8000
#define B_BUTTON 0x4000
#define Z_TRIG 0x2000
#define START_BUTTON 0x1000
#define U_JPAD 0x0800
#define D_JPAD 0x0400
#define L_JPAD 0x0200
#define R_JPAD 0x0100
#define L_TRIG 0x0020
#define R_TRIG 0x0010
#define U_CBUTTONS 0x0008
#define D_CBUTTONS 0x0004
#define L_CBUTTONS 0x0002
#define R_CBUTTONS 0x0001
#endif
