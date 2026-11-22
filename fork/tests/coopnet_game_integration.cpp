// Process-level test driver. Python launches a real coordinator and two clients.
#include "libcoopnet.h"
#include "server.hpp"
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <thread>

extern StunTurnServer sStunServer;
static bool host, requested, done, peerReady;
static uint64_t me, owner, lobby, remote;
extern "C" void game_init(int), game_begin(void), game_tick(void);
extern "C" int game_done(void);
extern "C" void game_receive(const uint8_t*, uint32_t);
extern "C" double game_time(void) {
    static auto start = std::chrono::steady_clock::now();
    return std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
}
extern "C" void game_transport_send(const uint8_t *p, uint32_t n) {
    uint64_t to = host ? remote : owner;
    if (to) coopnet_send_to(to, p, n);
}
static void connected(uint64_t id) {
    me = id;
    printf("CONNECTED %llu\n", (unsigned long long)id); fflush(stdout);
    if (host) coopnet_lobby_create("test", "1", "test", "test", 4, "", "test");
    else coopnet_lobby_list_get("test", "");
}
static void listed(uint64_t id, uint64_t, uint16_t, uint16_t, const char*, const char*, const char*, const char*, const char*) {
    if (!lobby) { lobby = id; coopnet_lobby_join(id, ""); }
}
static void joined(uint64_t l, uint64_t user, uint64_t o, uint64_t) {
    if (lobby && lobby != l) return;
    lobby = l; owner = o;
    if (user != me) remote = user;
    printf("JOINED self=%d owner=%d\n", user == me, owner == me); fflush(stdout);
    if (!host && owner && !requested) {
        requested = true;
        game_begin();
        puts("GAME_REQUEST_QUEUED"); fflush(stdout);
    }
}
static void peer(uint64_t) { peerReady = true; puts("PEER_READY"); fflush(stdout); }
static void receive(uint64_t from, const uint8_t* p, uint64_t n) {
    if (host) remote = from;
    game_receive(p, (uint32_t)n);
}
static void error(MPacketErrorNumber e, uint64_t) { printf("ERROR %d\n", int(e)); fflush(stdout); }
int main(int argc, char** argv) {
    if (argc != 3) return 2;
    int port = atoi(argv[2]);
    if (!strcmp(argv[1], "server")) {
        sStunServer.host = "127.0.0.1"; sStunServer.port = 9;
        gServer = new Server();
        if (!gServer->Begin(port)) return 3;
        puts("LISTENING"); fflush(stdout);
        for (;;) std::this_thread::sleep_for(std::chrono::seconds(1));
    }
    host = !strcmp(argv[1], "host");
    game_init(host);
    gCoopNetCallbacks.OnConnected = connected;
    gCoopNetCallbacks.OnLobbyListGot = listed;
    gCoopNetCallbacks.OnLobbyJoined = joined;
    gCoopNetCallbacks.OnPeerConnected = peer;
    gCoopNetCallbacks.OnReceive = receive;
    gCoopNetCallbacks.OnError = error;
    if (coopnet_begin("127.0.0.1", port, host ? "host" : "guest", host ? 1 : 2) != COOPNET_OK) return 4;
    auto start = std::chrono::steady_clock::now();
    while (std::chrono::steady_clock::now() - start < std::chrono::seconds(25)) {
        coopnet_update();
        game_tick();
        done = game_done();
        if (done) {
            // Leave the host alive long enough for duplicate requests/replies to settle.
            if (!host) for (int i = 0; i < 100; ++i) { coopnet_update(); std::this_thread::sleep_for(std::chrono::milliseconds(2)); }
            coopnet_shutdown(); coopnet_update(); return peerReady ? 0 : 5;
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(2));
    }
    fprintf(stderr, "TIMEOUT host=%d requested=%d peer=%d\n", host, requested, peerReady);
    coopnet_shutdown(); coopnet_update(); return 6;
}
