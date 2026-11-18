#pragma once
#include <stdint.h>
typedef struct VPADStatus { uint32_t hold, trigger, release; struct { uint16_t x,y,touched,validity; } tpNormal; } VPADStatus;
#define VPAD_BUTTON_MINUS 4
