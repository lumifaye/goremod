#include <assert.h>
#include <string.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdint.h>
#include <xsdk/gpu.h>
#include <xsdk/present.h>
#include <xsdk/xam.h>
#include "gfx_xbox360_window.h"
static int gpu_opens, gpu_closes, present_opens, present_closes, begins, ends, resolves, targets, steps;
static bool display_initializing;
static bool fail_gpu,fail_present,fail_begin,busy,ui_open;
NTSTATUS xsdk_gpu_open(void) { ++gpu_opens; return fail_gpu ? STATUS_UNSUCCESSFUL : STATUS_SUCCESS; }
NTSTATUS xsdk_gpu_close(void) { ++gpu_closes; return STATUS_SUCCESS; }
NTSTATUS xsdk_present_open(XsdkDisplayMode mode,uint32_t buffers,uint32_t interval,uint32_t *w,uint32_t *h) {
 assert(mode==XSDK_DISPLAY_720P && buffers==2 && interval==1);++present_opens;if(fail_present)return STATUS_UNSUCCESSFUL;display_initializing=true;*w=1280;*h=720;return STATUS_SUCCESS;
}
NTSTATUS xsdk_present_begin(uint32_t *addr,uint32_t timeout) { ++begins;assert(timeout==(display_initializing ? 5000u : 0u));display_initializing=false;if(busy)return STATUS_IO_TIMEOUT;if(fail_begin)return STATUS_UNSUCCESSFUL;*addr=0x1234;return STATUS_SUCCESS; }
void xsdk_present_end(void){++ends;}
void xsdk_present_close(void){++present_closes;}
void xsdk_gpu_resolve(uint32_t a,uint32_t w,uint32_t h,uint32_t c){assert(a==0x1234&&w==1280&&h==720&&c==0xff000000);++resolves;}
void xsdk_gpu_set_target(uint32_t w,uint32_t h){assert(w==1280&&h==720);++targets;}
bool xsdk_system_ui_open(void){return ui_open;}
void xsdk_log_write(const char *format,...){(void)format;}
static void iter(void){++steps;}
int main(void){
 char text[WAPI_CLIPBOARD_BUFSIZ+7]; memset(text, 'x', sizeof(text)-1); text[sizeof(text)-1]=0;
 gfx_xbox360_window.set_clipboard_text(text); assert(strlen(gfx_xbox360_window.get_clipboard_text())==WAPI_CLIPBOARD_BUFSIZ-1);
 gfx_xbox360_window.set_clipboard_text("paste"); gfx_xbox360_window.set_clipboard_text(gfx_xbox360_window.get_clipboard_text()+1);
 assert(!strcmp(gfx_xbox360_window.get_clipboard_text(),"aste")); gfx_xbox360_window.set_clipboard_text(NULL); assert(!*gfx_xbox360_window.get_clipboard_text());
 uint32_t w=0,h=0;
 gfx_xbox360_window.init("x");assert(gpu_opens==1&&present_opens==1&&begins==1&&resolves==1&&ends==1);
 gfx_xbox360_window.get_dimensions(&w,&h);assert(w==1280&&h==720&&gfx_xbox360_window.has_focus());
 ui_open=true;assert(!gfx_xbox360_window.has_focus());ui_open=false;
 busy=true;assert(!gfx_xbox360_window.start_frame());gfx_xbox360_window.swap_buffers_begin();assert(ends==1);busy=false;
 assert(gfx_xbox360_window.start_frame());assert(targets==1);assert(!gfx_xbox360_window.start_frame());
 gfx_xbox360_window.swap_buffers_begin();gfx_xbox360_window.swap_buffers_end();assert(ends==2&&resolves==2);
 gfx_xbox360_window.swap_buffers_begin();assert(ends==2);
 gfx_xbox360_window.main_loop(iter);assert(steps==1);gfx_xbox360_window.shutdown();
 assert(gpu_closes==1&&present_closes==1&&!gfx_xbox360_window.start_frame());
 fail_gpu=true;gfx_xbox360_window.init("x");assert(gpu_closes==1&&present_opens==1);fail_gpu=false;
 fail_present=true;gfx_xbox360_window.init("x");assert(gpu_closes==2&&present_closes==1);fail_present=false;
 fail_begin=true;gfx_xbox360_window.init("x");assert(gpu_closes==3&&present_closes==2);
}
