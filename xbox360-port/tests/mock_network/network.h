#ifndef TEST_NETWORK_H
#define TEST_NETWORK_H
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
typedef uint8_t u8; typedef uint16_t u16; typedef uint32_t u32; typedef uint64_t u64; typedef int16_t s16;
#define PACKET_LENGTH 3000
#define PACKET_DESTINATION_BROADCAST ((u8)-1)
#define SET_BIT(x,n) ((x) ? (1u<<(n)) : 0)
#define GET_BIT(x,n) (((x)>>(n)) & 1)
#define SOFT_ASSERT(x) ((void)0)
#define TRUE 1
enum PacketType { PACKET_ACK, PACKET_PLAYER, PACKET_TEST=42 };
enum PacketLevelMatchType { PLMT_NONE, PLMT_AREA, PLMT_LEVEL };
struct NetworkPlayer { u8 globalIndex; }; extern struct NetworkPlayer *gNetworkPlayerLocal;
struct Packet {
 enum PacketType packetType; u8 localIndex; u16 dataLength; u16 cursor; void *addr; bool error,writeError,reliable,levelAreaMustMatch,levelMustMatch,requestBroadcast,keepSendingAfterDisconnect; u8 destGlobalId; u16 seqId; bool sent; u8 orderedFromGlobalId; u16 orderedGroupId,orderedSeqId; u8 courseNum,actNum; s16 levelNum; u8 areaIndex; u8 buffer[PACKET_LENGTH];
};
u16 packet_seq_read_le(const struct Packet* p);
void packet_init(struct Packet*, enum PacketType, bool, enum PacketLevelMatchType);
void packet_write(struct Packet*, void*, u16);void packet_write_bytes(struct Packet*,const void*,u16);
void packet_read(struct Packet*,void*,u16);void packet_read_bytes(struct Packet*,void*,u16);
void packet_set_flags(struct Packet*);void packet_set_ordered_data(struct Packet*);
void packet_ordered_begin(void);void packet_ordered_end(void);void packet_duplicate(struct Packet*,struct Packet*);
u8 packet_initial_read(struct Packet*);u32 packet_hash(struct Packet*);bool packet_check_hash(struct Packet*);
#endif
