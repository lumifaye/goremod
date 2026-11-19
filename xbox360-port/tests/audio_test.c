#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <xsdk/audio.h>
#include "audio_xbox360.h"
static float audio_frame[XSDK_AUDIO_FRAME_FLOATS];
static int queued, playing, capacity=8, closed;
static float last_left,last_right;
NTSTATUS xsdk_audio_open(uint32_t ahead) { (void)ahead; queued=playing=closed=0; return STATUS_SUCCESS; }
NTSTATUS xsdk_audio_next_frame(uint32_t timeout, float **frame) {
    assert(timeout==0);
    if(queued-playing>=capacity)return STATUS_TIMEOUT;
    *frame=audio_frame; return STATUS_SUCCESS;
}
void xsdk_audio_queue_frame(void) {
    last_left=audio_frame[0];last_right=audio_frame[XSDK_AUDIO_FRAME_SAMPLES];
    for(unsigned i=2*XSDK_AUDIO_FRAME_SAMPLES;i<XSDK_AUDIO_FRAME_FLOATS;i++) assert(audio_frame[i]==0.0f);
    queued++;
}
void xsdk_audio_stats(XsdkAudioStats *stats) { memset(stats,0,sizeof(*stats));stats->played=playing; }
NTSTATUS xsdk_audio_close(void) { closed++;return STATUS_SUCCESS; }
int main(void) {
 int16_t in[768*2];for(unsigned i=0;i<768;i++){in[2*i]=16384;in[2*i+1]=-8192;}
 assert(audio_xbox360.init());audio_xbox360.play((uint8_t*)in,sizeof(in));
 assert(queued==4);assert(fabsf(last_left-.5f)<0.00001f);assert(fabsf(last_right+.25f)<0.00001f);
 int before=audio_xbox360.buffered();playing=2;assert(audio_xbox360.buffered()<before);
 capacity=0;audio_xbox360.play((uint8_t*)in,sizeof(in));assert(queued==4);assert(audio_xbox360.buffered()>0);
 audio_xbox360.shutdown();assert(closed==1 && audio_xbox360.buffered()==0);
 audio_xbox360.play((uint8_t*)in,sizeof(in));assert(queued==4);
 puts("xSDK audio frame conversion and queue mocks: passed");
}
