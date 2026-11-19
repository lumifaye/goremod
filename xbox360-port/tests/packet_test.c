#include "network.h"
#include "game/area.h"
#ifdef PPC_FREESTANDING
void *memcpy(void *dst,const void *src,size_t n){u8 *d=dst;const u8 *s=src;while(n--)*d++=*s++;return dst;}
void *memset(void *dst,int x,size_t n){u8 *d=dst;while(n--)*d++=(u8)x;return dst;}
#endif
s16 gCurrCourseNum=3,gCurrActStarNum=4,gCurrLevelNum=0x1234,gCurrAreaIndex=5;
struct NetworkPlayer player={7};struct NetworkPlayer *gNetworkPlayerLocal=&player;
static int equal(const u8*a,const u8*b,unsigned n){while(n--)if(*a++!=*b++)return 0;return 1;}
static int test(void){
 struct Packet p={0},copy={0};u32 val=0x12345678,back=0;u16 val16=0xabcd,back16=0;
 const u8 wire[]={42,1,0,1,255,3,4,0x34,0x12,5,0x78,0x56,0x34,0x12,0xcd,0xab,0x11,0x22,0x33,0x44};
 const u8 raw[]={0x11,0x22,0x33,0x44};u8 rawback[4];
 packet_init(&p,PACKET_TEST,true,PLMT_AREA);packet_write(&p,&val,4);packet_write(&p,&val16,2);packet_write_bytes(&p,raw,4);
 if(p.dataLength!=sizeof(wire)||!equal(p.buffer,wire,sizeof(wire)))return 1;
 p.cursor=3;packet_initial_read(&p);if(p.packetType!=PACKET_TEST||p.levelNum!=0x1234||p.courseNum!=3||p.actNum!=4||p.areaIndex!=5)return 2;
 packet_read(&p,&back,4);packet_read(&p,&back16,2);packet_read_bytes(&p,rawback,4);if(back!=val||back16!=val16||!equal(rawback,raw,4))return 3;
 packet_duplicate(&p,&copy);if(copy.buffer[1]!=2||copy.buffer[2]!=0)return 4;
 packet_ordered_begin();packet_init(&p,PACKET_PLAYER,false,PLMT_NONE);packet_set_ordered_data(&p);packet_ordered_end();
 if(p.buffer[0]!=PACKET_PLAYER||p.buffer[3]!=4||p.buffer[5]!=7||p.buffer[6]!=1||p.buffer[7]!=0||p.buffer[8]!=1||p.buffer[9]!=0)return 5;
 return 0;
}
#ifdef PPC_FREESTANDING
__attribute__((noreturn)) void _start(void){int status=test();register int n __asm__("r0")=1;register int s __asm__("r3")=status;__asm__ volatile("sc"::"r"(n),"r"(s):"memory");for(;;){}}
#else
int main(void){return test();}
#endif
