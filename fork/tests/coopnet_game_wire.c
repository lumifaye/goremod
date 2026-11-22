// Drives real game packet codec, retry queue, ordered queue and compression
// through the real CoopNet transport. Game state/packet handlers are stubs.
#include "network.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>

s16 gCurrCourseNum, gCurrActStarNum, gCurrLevelNum, gCurrAreaIndex;
struct NetworkPlayer gNetworkPlayers[MAX_PLAYERS];
static struct NetworkPlayer local;
struct NetworkPlayer *gNetworkPlayerLocal = &local, *gNetworkPlayerServer;
static bool is_host, sent_group, complete, dropped_request, dropped_header;
static unsigned processed;
static const enum PacketType expected[] = {PACKET_MOD_LIST, PACKET_MOD_LIST_ENTRY, PACKET_MOD_LIST_DONE};
extern void game_transport_send(const u8 *, u32);
extern double game_time(void);
extern void packet_compress(struct Packet*, u8**, u32*);
extern bool packet_decompress(struct Packet*, u8*, u32);
struct PacketLinkedList;
extern struct PacketLinkedList *head;
f32 clock_elapsed(void) { return (f32)game_time(); }
void *network_duplicate_address(u8 i) { u8 *a = malloc(1); *a = i; return a; }
void network_send_to(u8 i, struct Packet *p) {
    (void)i;
    packet_set_flags(p);
    if (p->orderedGroupId && !p->sent) packet_set_ordered_data(p);
    p->localIndex = 0;
    network_remember_reliable(p);
    u32 hash = packet_hash(p);
    p->buffer[p->dataLength] = hash & 255;
    p->buffer[p->dataLength+1] = (hash >> 8) & 255;
    p->buffer[p->dataLength+2] = (hash >> 16) & 255;
    p->buffer[p->dataLength+3] = (hash >> 24) & 255;
    u8 *data = NULL; u32 len = 0;
    packet_compress(p, &data, &len);
    assert(data && len);
    game_transport_send(data, len);
    p->sent = true;
}
static void send_type(enum PacketType type) {
    struct Packet p = {0};
    packet_init(&p, type, true, PLMT_NONE);
    network_send_to(0, &p);
}
void packet_process(struct Packet *p) {
    if (p->packetType == PACKET_MOD_LIST_REQUEST && is_host) {
        if (!sent_group) {
            sent_group = true;
            packet_ordered_begin();
            for (int i=0; i<3; ++i) send_type(expected[i]);
            packet_ordered_end();
        }
    } else if (p->packetType == PACKET_ACK) {
        network_receive_ack(p);
    } else if (!is_host && p->packetType == expected[processed]) {
        ++processed;
        if (processed == 3) { complete = true; puts("GAME_ORDERED_DONE"); fflush(stdout); }
    } else {
        fprintf(stderr, "unexpected game packet %u at %u\n", p->packetType, processed);
        abort();
    }
}
void game_init(int host) { is_host = host; }
void game_begin(void) { send_type(PACKET_MOD_LIST_REQUEST); }
void game_tick(void) { network_update_reliable(); packet_ordered_update(); }
int game_done(void) { return is_host ? (sent_group && head == NULL) : complete; }
void game_receive(const u8 *wire, u32 size) {
    struct Packet p = {0}; p.cursor = 3;
    assert(packet_decompress(&p, (u8*)wire, size));
    assert(packet_check_hash(&p));
    // Drop the first request and first mod-list header before the game sees
    // them, forcing genuine reliable retransmissions and out-of-order data.
    if (is_host && p.buffer[0] == PACKET_MOD_LIST_REQUEST && !dropped_request) {
        dropped_request = true; puts("GAME_DROP_REQUEST"); fflush(stdout); return;
    }
    if (!is_host && p.buffer[0] == PACKET_MOD_LIST && !dropped_header) {
        dropped_header = true; puts("GAME_DROP_HEADER"); fflush(stdout); return;
    }
    network_send_ack(&p);
    assert(packet_initial_read(&p) && !p.error);
    if (p.orderedGroupId) packet_ordered_add(&p); else packet_process(&p);
}
