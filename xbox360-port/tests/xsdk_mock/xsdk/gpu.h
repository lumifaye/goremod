#ifndef XSDK_MOCK_GPU_H
#define XSDK_MOCK_GPU_H
#include <stdint.h>
#include "xsdk/kernel.h"
NTSTATUS xsdk_gpu_open(void);
NTSTATUS xsdk_gpu_close(void);
void xsdk_gpu_resolve(uint32_t address, uint32_t width, uint32_t height, uint32_t clear_argb);
void xsdk_gpu_set_target(uint32_t width, uint32_t height);
#endif
