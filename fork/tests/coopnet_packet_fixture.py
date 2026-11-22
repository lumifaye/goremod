"""Build actual game packet modules against a minimal simulated game."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]

def prepare(tmp, source):
    header = (source / 'packet.h').read_text()
    enums = header[header.index('enum PacketType {'):header.index('enum KickReasonType {')]
    packet_dir = tmp / 'network/packets'; packet_dir.mkdir(parents=True)
    includes = tmp / 'include'; shutil.copytree(ROOT / 'xbox360-port/tests/include', includes)
    (includes / 'pc/utils').mkdir(); (includes / 'pc/utils/misc.h').write_text('')
    (includes / 'pc/debuglog.h').write_text('#define LOG_INFO(...) ((void)0)\n#define LOG_ERROR(...) ((void)0)\n')
    network = '''#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <stdlib.h>
#include <assert.h>
typedef uint8_t u8; typedef uint16_t u16; typedef uint32_t u32; typedef uint64_t u64;
typedef int16_t s16; typedef int32_t s32; typedef float f32;
#define PACKET_LENGTH 3000
#define PACKET_DESTINATION_BROADCAST ((u8)-1)
#define MAX_PLAYERS 16
#define SET_BIT(x,n) ((x) ? (1u<<(n)) : 0)
#define GET_BIT(x,n) (((x)>>(n)) & 1)
#define SOFT_ASSERT(x) assert(x)
#define MIN(a,b) ((a)<(b)?(a):(b))
#define TRUE 1
''' + enums + '''
struct NetworkPlayer { u8 globalIndex, localIndex; f32 ping; };
extern struct NetworkPlayer *gNetworkPlayerLocal, *gNetworkPlayerServer, gNetworkPlayers[MAX_PLAYERS];
f32 clock_elapsed(void); void* network_duplicate_address(u8); void network_send_to(u8, struct Packet*);
void packet_init(struct Packet*, enum PacketType, bool, enum PacketLevelMatchType);
void packet_write(struct Packet*, void*, u16); void packet_write_bytes(struct Packet*,const void*,u16);
void packet_read(struct Packet*,void*,u16); void packet_read_bytes(struct Packet*,void*,u16);
void packet_set_flags(struct Packet*); void packet_set_ordered_data(struct Packet*);
void packet_ordered_begin(void); void packet_ordered_end(void); void packet_duplicate(struct Packet*,struct Packet*);
u8 packet_initial_read(struct Packet*); u32 packet_hash(struct Packet*); bool packet_check_hash(struct Packet*);
u16 packet_seq_read_le(const struct Packet*);
void network_remember_reliable(struct Packet*); void network_update_reliable(void); void network_forget_all_reliable(void);
void network_send_ack(struct Packet*); void network_receive_ack(struct Packet*);
void packet_ordered_add(struct Packet*); void packet_ordered_clear_all(void); void packet_ordered_update(void); void packet_process(struct Packet*);
'''
    (tmp / 'network/network.h').write_text(network)
    for name in ('packet_read_write.c','packet_reliable.c','packet_ordered.c'):
        shutil.copy(source / name, packet_dir / name)
    return includes, packet_dir
