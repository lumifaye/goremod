/* Hardware bring-up only. This is NOT the game. */
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include <xsdk/gpu.h>
#include <xsdk/kernel.h>
#include <xsdk/log.h>
#include <xsdk/present.h>
#include "controller_xbox360.h"
#include "audio_xbox360.h"

bool configDisableGamepads = false;
unsigned int configGamepadNumber = 0;
static int16_t pcm[534 * 2];
static uint32_t phase;

static void make_tone(bool enabled, unsigned frames) {
    for (unsigned i = 0; i < frames; ++i) {
        int16_t s = enabled ? ((phase < 16000) ? 5000 : -5000) : 0;
        pcm[i * 2] = pcm[i * 2 + 1] = s;
        phase += 440;
        if (phase >= 32000) phase -= 32000;
    }
}
int main(void) {
    xsdk_log_write("Realism64 Xbox 360 diagnostic: NOT THE GAME. A = sound, Back = exit.");
    NTSTATUS r = xsdk_gpu_open();
    if (!NT_SUCCESS(r)) { xsdk_log_write("gpu_open failed: %08X", (unsigned)r); return 1; }
    uint32_t width=0,height=0;
    r = xsdk_present_open(XSDK_DISPLAY_720P, 2, 1, &width, &height);
    if (!NT_SUCCESS(r)) { xsdk_log_write("present_open failed: %08X", (unsigned)r); xsdk_gpu_close(); return 2; }
    controller_xbox360.init();
    bool have_audio = audio_xbox360.init();
    xsdk_log_write("Display %ux%u, audio=%s",(unsigned)width,(unsigned)height,have_audio ? "open" : "failed");
    for (uint32_t n=0;;n++) {
        OSContPad pad={0};
        controller_xbox360.read(&pad);
        if (pad.button & L_TRIG) break;
        if (have_audio) {
            unsigned frames=(n % 3 == 0) ? 534u : 533u;
            make_tone((pad.button & A_BUTTON)!=0, frames);
            audio_xbox360.play((const uint8_t*)pcm, frames * 4);
        }
        uint32_t dest=0;
        r=xsdk_present_begin(&dest,5000);
        if (!NT_SUCCESS(r)) { xsdk_log_write("present_begin failed: %08X",(unsigned)r); break; }
        /* Xbox left stick controls red/green. A makes the display blue and plays a tone. */
        uint32_t red=(uint32_t)(pad.stick_x+80)*255/160;
        uint32_t green=(uint32_t)(pad.stick_y+80)*255/160;
        uint32_t blue=(pad.button&A_BUTTON)?255u:0u;
        xsdk_gpu_resolve(dest,width,height,0xff000000u | (red<<16) | (green<<8) | blue);
        xsdk_present_end();
    }
    if(have_audio) audio_xbox360.shutdown();
    controller_xbox360.shutdown();
    xsdk_present_close();xsdk_gpu_close();
    xsdk_log_write("Realism64 diagnostic exited");
    return 0;
}
