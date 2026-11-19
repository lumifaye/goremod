/* Experimental xSDK audio backend: 32 kHz S16 stereo -> 48 kHz six-channel float. */
#if defined(TARGET_XBOX360) && defined(__XSDK__)
#include <stdint.h>
#include <string.h>
#include <xsdk/audio.h>
#include "audio_api.h"

/* The game calls the AudioAPI from its audio producer. XSDK owns playback. */
enum { INPUT_FRAMES = 8192, OUTPUT_SAMPLES = XSDK_AUDIO_FRAME_SAMPLES };
static int16_t ring[INPUT_FRAMES][2];
static unsigned head, count, phase;
static uint32_t queued;
static bool open;

static bool xbox_audio_init(void) {
    head = count = phase = queued = 0;
    open = xsdk_audio_open(0) == STATUS_SUCCESS;
    return open;
}
static int xbox_audio_buffered(void) {
    if (!open) return 0;
    XsdkAudioStats stats;
    xsdk_audio_stats(&stats);
    /* queued/played are frame counters (256 samples per 48 kHz frame). */
    uint32_t pending = queued >= stats.played ? queued - stats.played : 0;
    if (pending > XSDK_AUDIO_FRAMES_AHEAD_MAX) pending = XSDK_AUDIO_FRAMES_AHEAD_MAX;
    return (int)count + (int)((pending * OUTPUT_SAMPLES * 2u) / 3u);
}
static int xbox_audio_desired(void) { return 1100; }

/* 48 kHz / 32 kHz = 3/2. Linear interpolation keeps the fractional phase
 * across play calls and across hardware frames; one input frame is lookahead. */
static void xbox_audio_drain(void) {
    while (count > (phase + 2u * (OUTPUT_SAMPLES - 1u)) / 3u + 1u) {
        float *frame = 0;
        if (xsdk_audio_next_frame(0, &frame) != STATUS_SUCCESS || !frame) break;
        memset(frame, 0, XSDK_AUDIO_FRAME_FLOATS * sizeof(float));
        for (unsigned i = 0; i < OUTPUT_SAMPLES; ++i) {
            unsigned a = (head + phase / 3u) % INPUT_FRAMES;
            unsigned b = (a + 1u) % INPUT_FRAMES;
            unsigned f = phase % 3u;
            for (unsigned ch = 0; ch < 2; ++ch) {
                float mixed = ((float)ring[a][ch] * (3u - f) + (float)ring[b][ch] * f) / 3.0f;
                frame[ch * OUTPUT_SAMPLES + i] = mixed / 32768.0f;
            }
            phase += 2;
        }
        unsigned consumed = phase / 3u;
        head = (head + consumed) % INPUT_FRAMES;
        count -= consumed;
        phase %= 3u;
        xsdk_audio_queue_frame();
        ++queued;
    }
}
static void xbox_audio_play(const uint8_t *buf, size_t len) {
    if (!open || !buf) return;
    xbox_audio_drain();
    size_t frames = len / (2 * sizeof(int16_t));
    for (size_t i = 0; i < frames && count < INPUT_FRAMES; ++i) {
        unsigned at = (head + count) % INPUT_FRAMES;
        memcpy(&ring[at][0], buf + i * 4, sizeof(int16_t));
        memcpy(&ring[at][1], buf + i * 4 + 2, sizeof(int16_t));
        ++count;
    }
    xbox_audio_drain();
}
static void xbox_audio_shutdown(void) {
    if (open) xsdk_audio_close();
    open = false; head = count = phase = queued = 0;
}
struct AudioAPI audio_xbox360 = {
    .init = xbox_audio_init,
    .buffered = xbox_audio_buffered,
    .get_desired_buffered = xbox_audio_desired,
    .play = xbox_audio_play,
    .shutdown = xbox_audio_shutdown,
};
#endif
