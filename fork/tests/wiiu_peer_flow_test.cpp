#include <cassert>
#include <cstring>
#include <string>
#include "client.hpp"
#include "mpacket.hpp"
#include "libcoopnet.h"
static std::string calls;
static int connected=0, disconnected=0, sdpResult=0;
Client* gClient = nullptr;
CoopNetCallbacks gCoopNetCallbacks = {};
Client::~Client() {}
Connection::Connection(uint64_t id) { mId = id; }
Connection::~Connection() {}
float clock_elapsed() { return 1; }
static juice_config_t ice;
extern "C" juice_agent_t* juice_create(const juice_config_t* config) { ice = *config; return reinterpret_cast<juice_agent_t*>(1); }
extern "C" void juice_destroy(juice_agent_t*) {}
extern "C" void juice_set_log_level(juice_log_level_t) {}
extern "C" int juice_set_remote_description(juice_agent_t*, const char*) { calls += 'R'; return sdpResult; }
extern "C" int juice_gather_candidates(juice_agent_t*) { calls += 'G'; return 0; }
extern "C" int juice_get_local_description(juice_agent_t*, char* b, size_t size) { calls += 'L'; if(size) b[0]=0; return 0; }
extern "C" int juice_set_remote_gathering_done(juice_agent_t*) { calls += 'D'; return 0; }
extern "C" int juice_get_selected_candidates(juice_agent_t*, char*, size_t, char*, size_t) { return -1; }
extern "C" const char* juice_state_to_string(juice_state_t) { return "state"; }
void MPacket::Send(Connection&) { calls += 'S'; }
bool MPacketPeerSdp::Receive(Connection*) { return true; }
bool MPacketPeerCandidate::Receive(Connection*) { return true; }
bool MPacketPeerCandidateDone::Receive(Connection*) { return true; }
static int sendResult;
extern "C" int juice_send(juice_agent_t*, const char*, size_t) { return sendResult; }
static void on_connected(uint64_t) { ++connected; }
static void on_disconnected(uint64_t) { ++disconnected; }
int main() {
    Client c; Connection socket(0); c.mConnection = &socket; gClient = &c;
    gCoopNetCallbacks.OnPeerConnected=on_connected; gCoopNetCallbacks.OnPeerDisconnected=on_disconnected;
    c.mCurrentUserId=50;
    { Peer p(&c,10,1); assert(calls.empty()); p.Connect("sdp"); assert(calls=="RLSG"); p.CandidateDone(); assert(calls=="RLSGD");
      char candidate[] = "candidate:test";
      ice.cb_candidate(nullptr, candidate, ice.user_ptr); candidate[0] = 0;
      ice.cb_gathering_done(nullptr, ice.user_ptr);
      assert(calls == "RLSGD" && c.mEvents.size() == 2);
      assert(c.mEvents[0].type == PEER_EVENT_CANDIDATE && c.mEvents[0].candidate == "candidate:test");
      assert(c.mEvents[1].type == PEER_EVENT_GATHERING_DONE && c.mEvents[1].peerId == p.mId);
      p.OnStateChanged(JUICE_STATE_GATHERING); p.OnStateChanged(JUICE_STATE_CONNECTING);
      p.OnStateChanged(JUICE_STATE_CONNECTED); p.OnStateChanged(JUICE_STATE_COMPLETED);
      assert(p.Send(nullptr, 0)); sendResult=-1; assert(!p.Send(nullptr, 0));
      assert(connected==1); p.OnStateChanged(JUICE_STATE_DISCONNECTED); p.OnStateChanged(JUICE_STATE_FAILED); assert(disconnected==1); }
    calls.clear(); c.mCurrentUserId=10;
    { Peer p(&c,50,1); assert(calls=="LS"); calls.clear(); p.Connect("sdp"); assert(calls=="RG"); p.CandidateDone(); assert(calls=="RGD"); }
    calls.clear(); c.mCurrentUserId=50; sdpResult=-1;
    { Peer p(&c,10,1); p.Connect("invalid"); assert(calls=="R"); }
}
