/* Experimental xSDK display/presentation layer. A 3D renderer is still required. */
#if defined(TARGET_XBOX360) && defined(__XSDK__)
#include <stdbool.h>
#include <stdint.h>
#include <time.h>
#include <string.h>
#include <xsdk/gpu.h>
#include <xsdk/present.h>
#include <xsdk/xam.h>
#include <xsdk/log.h>
#include "gfx_window_manager_api.h"

static bool gpu_opened, display_opened, frame_open;
static uint32_t display_width, display_height, frame_address;
static char clipboard[WAPI_CLIPBOARD_BUFSIZ];

static void xbox_window_shutdown(void);
static void xbox_window_init(const char *title) {
    (void)title;
    if (gpu_opened || display_opened) xbox_window_shutdown();
    NTSTATUS status = xsdk_gpu_open();
    if (!NT_SUCCESS(status)) { xsdk_log_write("xbox window: GPU open failed: %08X", (unsigned)status); return; }
    gpu_opened = true;
    status = xsdk_present_open(XSDK_DISPLAY_720P, 2, 1, &display_width, &display_height);
    if (!NT_SUCCESS(status)) { xsdk_log_write("xbox window: display open failed: %08X", (unsigned)status); xbox_window_shutdown(); return; }
    display_opened = true;
    /* A resolve clears eDRAM after copying; prime it before the first game frame. */
    uint32_t address;
    status = xsdk_present_begin(&address, 5000);
    if (!NT_SUCCESS(status)) { xsdk_log_write("xbox window: initial frame failed: %08X", (unsigned)status); xbox_window_shutdown(); return; }
    xsdk_gpu_resolve(address, display_width, display_height, 0xff000000u);
    xsdk_present_end();
}
static void xbox_keyboard_callbacks(kb_callback_t a,kb_callback_t b,void (*c)(void),void (*d)(char*),void (*e)(char*,int)) { (void)a;(void)b;(void)c;(void)d;(void)e; }
static void xbox_scroll_callback(void (*f)(float,float)) { (void)f; }
static void xbox_main_loop(void (*iteration)(void)) { if (iteration) iteration(); }
static void xbox_dimensions(uint32_t *w,uint32_t *h) { if(w)*w=display_width; if(h)*h=display_height; }
static void xbox_events(void) {}
static bool xbox_start_frame(void) {
    if (!display_opened || frame_open) return false;
    // Gameplay also feeds audio on this thread. Never wait seconds for a
    // late vblank/fence: leave the old frame displayed and retry next tick.
    NTSTATUS status=xsdk_present_begin(&frame_address,0);
    if (status == STATUS_IO_TIMEOUT) {
        static unsigned misses;
        if (++misses && !(misses & (misses - 1)))
            xsdk_log_write("xbox present: buffer busy, skipped %u frames so far", misses);
        return false;
    }
    if (!NT_SUCCESS(status)) { xsdk_log_write("xbox window: begin frame failed: %08X",(unsigned)status); return false; }
    frame_open = true;
    xsdk_gpu_set_target(display_width, display_height);
    return true;
}
static void (*scanout)(uint32_t,uint32_t,uint32_t);
void xbox_set_scanout(void (*fn)(uint32_t,uint32_t,uint32_t)) { scanout=fn; }
static void xbox_swap_begin(void) {
    if (!frame_open) return;
    if (scanout) scanout(frame_address,display_width,display_height);
    else xsdk_gpu_resolve(frame_address,display_width,display_height,0xff000000u);
    xsdk_present_end();
    frame_open=false;
}
static void xbox_swap_end(void) {}
static double xbox_get_time(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC,&t)) return 0.0;
    return (double)t.tv_sec+(double)t.tv_nsec/1000000000.0;
}
static void xbox_window_shutdown(void) {
    if(display_opened) xsdk_present_close();
    if(gpu_opened) xsdk_gpu_close();
    gpu_opened=display_opened=frame_open=false;
    display_width=display_height=frame_address=0;
}
static void xbox_noop(void) {}
static char *xbox_clipboard_get(void) { return clipboard; }
static void xbox_clipboard_set(const char *text) {
    size_t n = text ? strnlen(text, sizeof clipboard - 1) : 0;
    if (n) memmove(clipboard, text, n);
    clipboard[n] = 0;
}
static void xbox_cursor(bool visible) { (void)visible; }
static void xbox_delay(unsigned int ms) {
    struct timespec t={(time_t)(ms/1000u),(long)(ms%1000u)*1000000L};
    nanosleep(&t,0);
}
static int xbox_max_msaa(void) { return 0; }
static void xbox_title(const char *title) { (void)title; }
static bool xbox_focused(void) { return display_opened && !xsdk_system_ui_open(); }

struct GfxWindowManagerAPI gfx_xbox360_window = {
    .init=xbox_window_init, .set_keyboard_callbacks=xbox_keyboard_callbacks,
    .set_scroll_callback=xbox_scroll_callback, .main_loop=xbox_main_loop,
    .get_dimensions=xbox_dimensions, .handle_events=xbox_events, .start_frame=xbox_start_frame,
    .swap_buffers_begin=xbox_swap_begin, .swap_buffers_end=xbox_swap_end,
    .get_time=xbox_get_time, .shutdown=xbox_window_shutdown, .start_text_input=xbox_noop,
    .stop_text_input=xbox_noop, .get_clipboard_text=xbox_clipboard_get,
    .set_clipboard_text=xbox_clipboard_set, .set_cursor_visible=xbox_cursor,
    .delay=xbox_delay, .get_max_msaa=xbox_max_msaa, .set_window_title=xbox_title,
    .reset_window_title=xbox_noop, .has_focus=xbox_focused,
};
#endif
