#ifndef XSDK_MOCK_PRESENT_H
#define XSDK_MOCK_PRESENT_H
#include <stdint.h>
#include "xsdk/display.h"
NTSTATUS xsdk_present_open(XsdkDisplayMode mode, uint32_t buffer_count, uint32_t swap_interval,
                           uint32_t *width, uint32_t *height);
NTSTATUS xsdk_present_begin(uint32_t *address, uint32_t timeout_ms);
void xsdk_present_end(void);
void xsdk_present_close(void);
#endif
