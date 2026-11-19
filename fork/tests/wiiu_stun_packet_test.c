#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "stun.h"
static void verify(unsigned char *packet, size_t size, unsigned wanted) {
 const unsigned char expected[8] = {1,2,3,4,5,6,7,8};
 int found=0;
 for(size_t i=20;i+4<=size;) {
  unsigned type=((unsigned)packet[i]<<8)|packet[i+1];
  unsigned length=((unsigned)packet[i+2]<<8)|packet[i+3];
  assert(i+4+length<=size);
  if(type==wanted) { assert(length==8 && memcmp(packet+i+4,expected,8)==0); found++; }
  i+=4+((length+3)&~3u);
 }
 assert(found==1);
}
int main(void) {
 stun_message_t msg={0}, parsed={0}; unsigned char packet[512];
 msg.msg_class=STUN_CLASS_REQUEST; msg.msg_method=STUN_METHOD_BINDING;
 msg.ice_controlling=msg.ice_controlled=msg.reservation_token=UINT64_C(0x0102030405060708);
 int n=stun_write(packet,sizeof(packet),&msg,"test-password"); assert(n>0);
 verify(packet,n,STUN_ATTR_ICE_CONTROLLING);verify(packet,n,STUN_ATTR_ICE_CONTROLLED);verify(packet,n,STUN_ATTR_RESERVATION_TOKEN);
 assert(stun_read(packet,n,&parsed)==n);assert(parsed.ice_controlling==msg.ice_controlling);
 assert(parsed.ice_controlled==msg.ice_controlled);assert(parsed.reservation_token==msg.reservation_token);
 assert(stun_check_integrity(packet,n,&parsed,"test-password"));
 assert(!stun_check_integrity(packet,n,&parsed,"wrong-password"));
 puts("STUN packet attributes and message integrity: ok");
}
