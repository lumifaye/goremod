#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include <xsdk/kernel.h>
#include <xsdk/audio.h>
#include <xsdk/gpu.h>
#include <xsdk/present.h>
static unsigned input_count, opened_gpu, closed_gpu, opened_display, closed_display, frames, queued, closed_audio;
static float audio_frame[XSDK_AUDIO_FRAME_FLOATS];
extern int diagnostic_main(void);
void xsdk_log_write(const char *format,...) { (void)format; }
NTSTATUS xsdk_gpu_open(void){opened_gpu++;return STATUS_SUCCESS;}
NTSTATUS xsdk_gpu_close(void){closed_gpu++;return STATUS_SUCCESS;}
NTSTATUS xsdk_present_open(XsdkDisplayMode mode,uint32_t count,uint32_t interval,uint32_t *w,uint32_t *h){(void)mode;(void)count;(void)interval;opened_display++;*w=1280;*h=720;return STATUS_SUCCESS;}
NTSTATUS xsdk_present_begin(uint32_t *addr,uint32_t timeout){assert(timeout==5000);*addr=0x1234;return STATUS_SUCCESS;}
void xsdk_gpu_resolve(uint32_t addr,uint32_t w,uint32_t h,uint32_t color){assert(addr==0x1234&&w==1280&&h==720&&(color&255)==255);frames++;}
void xsdk_present_end(void){}
void xsdk_present_close(void){closed_display++;}
uint32_t XamInputGetState(uint32_t user,uint32_t flags,INPUT_STATE *state){assert(user==0&&flags==0);memset(state,0,sizeof(*state));state->gamepad.buttons=(input_count++==0)?INPUT_GAMEPAD_A:INPUT_GAMEPAD_BACK;return 0;}
uint32_t XamInputSetState(uint32_t user,uint32_t flags,const INPUT_VIBRATION *vibration){assert(user==0&&flags==0&&vibration);return 0;}
NTSTATUS xsdk_audio_open(uint32_t n){(void)n;return STATUS_SUCCESS;}
NTSTATUS xsdk_audio_next_frame(uint32_t timeout,float **frame){(void)timeout;*frame=audio_frame;return STATUS_SUCCESS;}
void xsdk_audio_queue_frame(void){queued++;assert(audio_frame[0] > 0.1f || audio_frame[0] < -0.1f);}
void xsdk_audio_stats(XsdkAudioStats *s){memset(s,0,sizeof(*s));}
NTSTATUS xsdk_audio_close(void){closed_audio++;return STATUS_SUCCESS;}
int main(void){assert(diagnostic_main()==0);assert(opened_gpu==1&&closed_gpu==1&&opened_display==1&&closed_display==1&&frames==1&&queued==3&&closed_audio==1);}
