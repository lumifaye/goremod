"""Run actual game reliable-queue code against a deterministic clock/transport."""
from pathlib import Path
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[2]
for platform in ('PC', 'Android', 'VR', 'WiiU'):
    text = (ROOT / platform / 'src/pc/network/packets/packet_reliable.c').read_text()
    code = '''#include <stdlib.h>
#include <stdbool.h>
#include <stdint.h>
#include <assert.h>
#include <string.h>
#define LOG_INFO(...) ((void)0)
#define LOG_ERROR(...) ((void)0)
#define SOFT_ASSERT(x) assert(x)
#define MIN(a,b) ((a)<(b)?(a):(b))
typedef float f32; typedef uint8_t u8; typedef uint16_t u16;
enum PacketType { PACKET_ACK, PACKET_JOIN_REQUEST, PACKET_MOD_LIST_REQUEST, PACKET_DOWNLOAD_REQUEST, PACKET_DOWNLOAD, PACKET_MOD_LIST, PACKET_MOD_LIST_ENTRY, PACKET_MOD_LIST_FILE, PACKET_MOD_LIST_DONE, PACKET_LUA_SYNC_TABLE };
#define PLMT_NONE 0
struct Packet { u8 buffer[32]; bool reliable,sent,writeError,keepSendingAfterDisconnect; void* addr; u8 localIndex; u16 seqId; enum PacketType packetType; };
struct NetworkPlayer { float ping; u8 localIndex; };
struct NetworkPlayer gNetworkPlayers[16], *gNetworkPlayerServer;
static float now; static int sends;
static float clock_elapsed(void) { return now; }
static void *network_duplicate_address(u8 i) { unsigned char *p=malloc(1); *p=i; return p; }
static void network_send_to(u8 i, struct Packet *p) { assert(i==0 && p->seqId==123 && p->sent); sends++; }
static u16 packet_seq_read_le(struct Packet *p) { return p->seqId; }
static void packet_init(struct Packet *p, enum PacketType t, bool r, int m) { (void)p;(void)t;(void)r;(void)m; }
static void packet_write(struct Packet *p, void *d, int n) { (void)p;(void)d;(void)n; }
static void packet_read(struct Packet *p, void *d, int n) { assert(n == 2); memcpy(d, &p->seqId, 2); }
''' + text[text.index('#define RELIABLE_RESEND_RATE'):] + '''
int main(void) {
    struct Packet p = { .reliable=true, .seqId=123, .packetType=PACKET_MOD_LIST_REQUEST };
    network_remember_reliable(&p);
    assert(head && head->sendAttempts==1);
    now = 0.6f; network_update_reliable(); assert(sends==0);
    now = 0.65f; network_update_reliable(); assert(sends==1 && head->sendAttempts==2);
    now = 1.5f; network_update_reliable(); assert(sends==2);
    struct Packet ack = { .seqId=123 }; network_receive_ack(&ack);
    assert(head==NULL && tail==NULL);
    now = 20; network_update_reliable(); assert(sends==2);
}
'''
    with tempfile.TemporaryDirectory() as folder:
        exe = str(Path(folder) / 'test')
        subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-x', 'c', '-', '-o', exe], input=code.encode(), check=True)
        subprocess.run([exe], check=True)
    print(platform, 'actual reliable retry and ACK ok')
