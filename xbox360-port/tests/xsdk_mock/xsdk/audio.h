#ifndef XSDK_MOCK_AUDIO_H
#define XSDK_MOCK_AUDIO_H
#include <stdint.h>
#include "xsdk/kernel.h"
enum { XSDK_AUDIO_CHANNELS = 6, XSDK_AUDIO_FRAME_SAMPLES = 256,
       XSDK_AUDIO_FRAME_FLOATS = XSDK_AUDIO_CHANNELS * XSDK_AUDIO_FRAME_SAMPLES,
       XSDK_AUDIO_FRAMES_AHEAD_MAX = 16 };
typedef struct { uint32_t played, silent, fewest_queued, longest_wait_us; } XsdkAudioStats;
NTSTATUS xsdk_audio_open(uint32_t frames_ahead);
NTSTATUS xsdk_audio_next_frame(uint32_t timeout_ms, float **frame);
void xsdk_audio_queue_frame(void);
void xsdk_audio_stats(XsdkAudioStats *stats);
NTSTATUS xsdk_audio_close(void);
#endif
