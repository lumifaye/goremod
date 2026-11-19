#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include "hash.h"
#include "hmac.h"
#include "stun_wire.h"
#ifdef PPC_FREESTANDING
void *memcpy(void *dst, const void *src, size_t n) { unsigned char *d=dst; const unsigned char *s=src; while(n--) *d++=*s++; return dst; }
void *memset(void *dst, int ch, size_t n) { unsigned char *d=dst; while(n--) *d++=(unsigned char)ch; return dst; }
#endif
static int equal(const unsigned char *a, const unsigned char *b, size_t n) { while(n--) if(*a++ != *b++)return 0; return 1; }
static int test(void) {
 const unsigned char sha1[] = {0xa9,0x99,0x3e,0x36,0x47,0x06,0x81,0x6a,0xba,0x3e,0x25,0x71,0x78,0x50,0xc2,0x6c,0x9c,0xd0,0xd8,0x9d};
 const unsigned char hmac[] = {0xb6,0x17,0x31,0x86,0x55,0x05,0x72,0x64,0xe2,0x8b,0xc0,0xb6,0xfb,0x37,0x8c,0x8e,0xf1,0x46,0xbe,0x00};
 const unsigned char sha256[] = {0xba,0x78,0x16,0xbf,0x8f,0x01,0xcf,0xea,0x41,0x41,0x40,0xde,0x5d,0xae,0x22,0x23,0xb0,0x03,0x61,0xa3,0x96,0x17,0x7a,0x9c,0xb4,0x10,0xff,0x61,0xf2,0x00,0x15,0xad};
 unsigned char out[32], key[20];
 const unsigned char wire[] = {1,2,3,4,5,6,7,8};
 stun_store_u64(out, UINT64_C(0x0102030405060708)); if (!equal(out, wire, 8)) return 4;
 hash_sha1("abc",3,out); if(!equal(out,sha1,20)) return 1;
 memset(key,0x0b,sizeof(key)); hmac_sha1("Hi There",8,key,sizeof(key),out); if(!equal(out,hmac,20)) return 2;
 hash_sha256("abc",3,out); if(!equal(out,sha256,32)) return 3;
 return 0;
}
#ifdef PPC_FREESTANDING
__attribute__((noreturn)) void _start(void) { int status=test(); register int nr __asm__("r0")=1; register int code __asm__("r3")=status; __asm__ volatile("sc" : : "r"(nr), "r"(code) : "memory"); for(;;){} }

#else
int main(void) { return test(); }
#endif
