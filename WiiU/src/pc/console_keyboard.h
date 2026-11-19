#pragma once
/* DJUI deals in UTF-8; the console owns the native dialog and its lifetime. */
#ifdef TARGET_XBOX360
#include <stdbool.h>
#include <stddef.h>
bool console_keyboard_open(const char *initial, size_t capacity, bool password);
bool console_keyboard_active(void);
void console_keyboard_cancel(void);
int console_keyboard_take_result(char *out, size_t capacity);
#elif defined(TARGET_WII_U)
#include "wiiu_keyboard.h"
#define console_keyboard_open wiiu_keyboard_open
#define console_keyboard_active wiiu_keyboard_active
#define console_keyboard_cancel wiiu_keyboard_cancel
#define console_keyboard_take_result wiiu_keyboard_take_result
#endif
