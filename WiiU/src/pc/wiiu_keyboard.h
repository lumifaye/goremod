#pragma once
#ifdef TARGET_WII_U
#include <stdbool.h>
#include <stddef.h>
typedef struct VPADStatus VPADStatus;
#ifdef __cplusplus
extern "C" {
#endif
bool wiiu_keyboard_open(const char *initial, size_t max_bytes, bool password);
bool wiiu_keyboard_input(const VPADStatus *status);
bool wiiu_keyboard_active(void);
int wiiu_keyboard_take_result(char *out, size_t capacity);
void wiiu_keyboard_cancel(void);
void wiiu_keyboard_draw_drc(void);
void wiiu_keyboard_shutdown(void);
#ifdef __cplusplus
}
#endif
#endif
