#ifndef XSDK_MOCK_KERNEL_H
#define XSDK_MOCK_KERNEL_H
#include <stdint.h>
typedef int32_t NTSTATUS;
#define STATUS_SUCCESS ((NTSTATUS)0)
#define STATUS_IO_TIMEOUT ((NTSTATUS)0xC00000B5)
#define STATUS_TIMEOUT ((NTSTATUS)0x00000102)
#define STATUS_UNSUCCESSFUL ((NTSTATUS)0xC0000001)
#define NT_SUCCESS(status) ((NTSTATUS)(status) >= 0)
enum {
    INPUT_GAMEPAD_DPAD_UP = 0x0001,
    INPUT_GAMEPAD_DPAD_DOWN = 0x0002,
    INPUT_GAMEPAD_DPAD_LEFT = 0x0004,
    INPUT_GAMEPAD_DPAD_RIGHT = 0x0008,
    INPUT_GAMEPAD_START = 0x0010,
    INPUT_GAMEPAD_BACK = 0x0020,
    INPUT_GAMEPAD_LEFT_SHOULDER = 0x0100,
    INPUT_GAMEPAD_RIGHT_SHOULDER = 0x0200,
    INPUT_GAMEPAD_A = 0x1000,
    INPUT_GAMEPAD_B = 0x2000,
    INPUT_GAMEPAD_X = 0x4000,
    INPUT_GAMEPAD_Y = 0x8000,
};
typedef struct {
    uint16_t buttons;
    uint8_t left_trigger, right_trigger;
    int16_t thumb_lx, thumb_ly, thumb_rx, thumb_ry;
} INPUT_GAMEPAD;
typedef struct { uint32_t packet_number; INPUT_GAMEPAD gamepad; } INPUT_STATE;
typedef struct { uint16_t left_motor_speed, right_motor_speed; } INPUT_VIBRATION;
uint32_t XamInputGetState(uint32_t user_index, uint32_t flags, INPUT_STATE *state);
uint32_t XamInputSetState(uint32_t user_index, uint32_t flags, const INPUT_VIBRATION *vibration);
#endif
