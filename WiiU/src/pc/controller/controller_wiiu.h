#ifndef CONTROLLER_WIIU_H
#define CONTROLLER_WIIU_H

#include <stdbool.h>
#include "controller_api.h"

extern struct ControllerAPI controller_wiiu;
bool controller_wiiu_touch_pressed(float *x, float *y);
bool controller_wiiu_touch_state(float *x, float *y);

#endif
