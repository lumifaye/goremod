// Real packet serializer, retry queue and ordered receiver, with the game
// environment and transport stubbed. See coopnet_game_packets_test.py.
#include "network.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

s16 gCurrCourseNum, gCurrActStarNum, gCurrLevelNum, gCurrAreaIndex;
struct NetworkPlayer gNetworkPlayers[MAX_PLAYERS];
struct NetworkPlayer local = { .globalIndex = 0 }, *gNetworkPlayerLocal = &local, *gNetworkPlayerServer;
static f32 now;
static unsigned retries, acks, processed;
static u8 process_types[3];
f32 clock_elapsed(void) { return now; }
void *network_duplicate_address(u8 i) { u8 *p = malloc(1); *p = i; return p; }
void network_send_to(u8 i, struct Packet* p) {
    (void)i;
    if (p->packetType == PACKET_ACK) ++acks;
    else { assert(p->packetType == PACKET_MOD_LIST_REQUEST && p->sent); ++retries; }
}
void packet_process(struct Packet *p) {
    assert(processed < 3);
    process_types[processed++] = p->packetType;
}
static void deliver(struct Packet *original) {
    struct Packet p = *original;
    p.cursor = 3;
    network_send_ack(&p);
    assert(packet_initial_read(&p));
    assert(!p.error && p.orderedGroupId != 0);
    packet_ordered_add(&p);
}
static void acknowledge(struct Packet *original) {
    // ACK payload read uses the actual packet_read implementation.
    struct Packet p = {0};
    p.cursor = 0;
    packet_write(&p, &original->seqId, sizeof(original->seqId));
    p.cursor = 0;
    network_receive_ack(&p);
}
int main(void) {
    // The first transport attempt is lost before ICE is ready. The real
    // reliable queue must retry the same sequence, then stop on an ACK.
    struct Packet request = {0};
    packet_init(&request, PACKET_MOD_LIST_REQUEST, true, PLMT_NONE);
    network_remember_reliable(&request);
    now = 0.65f; network_update_reliable(); assert(retries == 1);
    acknowledge(&request);
    now = 10; network_update_reliable(); assert(retries == 1);

    // A host sends a real ordered mod-list group. Simulate packet reordering:
    // entry and done arrive before header; processing must still be header,
    // entry, done. Repeat entry to verify duplicate suppression in the group.
    struct Packet list[3] = {{0}};
    enum PacketType types[] = {PACKET_MOD_LIST, PACKET_MOD_LIST_ENTRY, PACKET_MOD_LIST_DONE};
    packet_ordered_begin();
    for (int i = 0; i < 3; ++i) {
        packet_init(&list[i], types[i], true, PLMT_NONE);
        packet_set_ordered_data(&list[i]);
        network_remember_reliable(&list[i]);
    }
    packet_ordered_end();
    deliver(&list[1]); deliver(&list[1]); deliver(&list[2]);
    assert(processed == 0);
    deliver(&list[0]);
    assert(processed == 3 && process_types[0] == types[0] && process_types[1] == types[1] && process_types[2] == types[2]);
    for (int i = 0; i < 3; ++i) acknowledge(&list[i]);
    assert(acks == 4);
    now = 20; network_update_reliable(); assert(retries == 1);
    packet_ordered_clear_all(); network_forget_all_reliable();
    puts("real packet encoding, retry/ACK and reordered duplicate mod-list group: ok");
}
