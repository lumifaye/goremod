#include <map>
#include <vector>
#include <mutex>
#include <cstdio>
#include <cstring>
#include <unistd.h>
#include "libcoopnet.h"
#include "peer.hpp"
#include "client.hpp"
#include "mpacket.hpp"
#include "logging.hpp"
#include "utils.hpp"
#ifdef __WIIU__
#include <coreinit/debug.h>
extern "C" void wiiu_coopnet_join_status(const char*, unsigned, unsigned, unsigned, unsigned, unsigned);
#define WIIU_PEER_TRACE(...) OSReport(__VA_ARGS__)
#else
#define WIIU_PEER_TRACE(...) ((void)0)
#endif

// Set to true to force TURN / relay usage for testing
static bool sForceRelay = false;

// ICE callbacks can run on a worker. Only Client::Update owns the signaling
// stream (and the Xbox partial-write queue); copy transient SDP before return.
static void sOnCandidate(juice_agent_t*, const char *sdp, void *user_ptr) {
    PeerEvent event = {};
    event.peerId = static_cast<Peer*>(user_ptr)->mId;
    event.type = PEER_EVENT_CANDIDATE;
    event.candidate = sdp;
    std::lock_guard<std::mutex> guard(gClient->mEventsMutex);
    gClient->mEvents.push_back(event);
}
static void sOnGatheringDone(juice_agent_t*, void *user_ptr) {
    PeerEvent event = {};
    event.peerId = static_cast<Peer*>(user_ptr)->mId;
    event.type = PEER_EVENT_GATHERING_DONE;
    std::lock_guard<std::mutex> guard(gClient->mEventsMutex);
    gClient->mEvents.push_back(event);
}

static void sOnStateChanged(juice_agent_t *agent, juice_state_t state, void *user_ptr) {
    Peer* peer = (Peer*)user_ptr;

    PeerEventStateChanged stateChanged = {
        .state = state
    };

    PeerEvent event = {
        .peerId = peer->mId,
        .type = PEER_EVENT_STATE_CHANGED,
        .data = { .stateChanged = stateChanged },
    };

    std::lock_guard<std::mutex> guard(gClient->mEventsMutex);
    gClient->mEvents.push_back(event);
}

static void sOnRecv(juice_agent_t *agent, const char *data, size_t size, void *user_ptr) {
    Peer* peer = (Peer*)user_ptr;

    PeerEventRecv recv = {
        .data = (const uint8_t*)malloc(size),
        .dataSize = size
    };
    if (!recv.data) return;
    memcpy((void*)recv.data, data, size);

    std::lock_guard<std::mutex> guard(gClient->mEventsMutex);
    gClient->mEvents.push_back({
        .peerId = peer->mId,
        .type = PEER_EVENT_RECV,
        .data = { .recv = recv },
    });
}

Peer::Peer(Client* aClient, uint64_t aId, uint32_t aPriority) {
    mId = aId;
    mPriority = aPriority;
    mLastState = JUICE_STATE_DISCONNECTED;
    mCurrentState = JUICE_STATE_DISCONNECTED;
    mTimeout = clock_elapsed() + PEER_TIMEOUT;
    mControlling = (gClient->mCurrentUserId < mId);

#ifdef LOGGING
    juice_set_log_level(JUICE_LOG_LEVEL_DEBUG);
#else
    juice_set_log_level(JUICE_LOG_LEVEL_NONE);
#endif

    // Agent 1: Create agent
    juice_config_t config;
    memset(&config, 0, sizeof(config));

    // STUN server example
    config.stun_server_host = aClient->mStunServer.host.c_str();
    config.stun_server_port = aClient->mStunServer.port;
    LOG_INFO("STUN server: %s, %u", config.stun_server_host, config.stun_server_port);

    // TURN server example (use your own server in production)
    if (aClient->mTurnServers.size() > 0) {
        mTurnServers = (juice_turn_server_t*)calloc(aClient->mTurnServers.size(), sizeof(juice_turn_server_t));
        if (!mTurnServers) {
            config.turn_servers = nullptr;
            config.turn_servers_count = 0;
            LOG_ERROR("Failed to allocate turn servers");
        } else {
            for (uint32_t i = 0; i < aClient->mTurnServers.size(); i++) {
                StunTurnServer* turn = &aClient->mTurnServers[i];
                mTurnServers[i].host = turn->host.c_str();
                mTurnServers[i].port = turn->port;
                mTurnServers[i].username = turn->username.c_str();
                mTurnServers[i].password = turn->password.c_str();
                LOG_INFO("TURN server: %s, %u", mTurnServers[i].host, mTurnServers[i].port);
            }
            config.turn_servers = mTurnServers;
            config.turn_servers_count = aClient->mTurnServers.size();
        }
    }

    config.cb_state_changed = sOnStateChanged;
    config.cb_candidate = sOnCandidate;
    config.cb_gathering_done = sOnGatheringDone;
    config.cb_recv = sOnRecv;
    config.user_ptr = this;
    config.concurrency_mode = JUICE_CONCURRENCY_MODE_POLL;

    mConnected = false;
    mAgent = juice_create(&config);
    WIIU_PEER_TRACE("coopnet peer: create role=%s agent=%s\n", mControlling ? "controlling" : "controlled", mAgent ? "ok" : "failed");

    // Send if it is an ICE controller
    if (mControlling) {
        SendSdp();
    }
}

Peer::~Peer() {
    if (mTurnServers) {
        free(mTurnServers);
        mTurnServers = nullptr;
    }
}

void Peer::Update() {
#ifdef __WIIU__
    // Report on either side, before the coordinator removes a timed-out joiner.
    if (!mConnected && !mJoinStatusShown && clock_elapsed() >= mTimeout - PEER_TIMEOUT + 12.0f) {
        mJoinStatusShown = true;
        unsigned sent, received, answered;
        juice_get_peer_checks(mAgent, &sent, &received, &answered);
        wiiu_coopnet_join_status(mAgent ? mJoinStage : "peer setup failed", mLocalCandidates, mRemoteCandidates, sent, received, answered);
    }
#endif
    // Check for peer connection fail
    if (!mConnected && mPriority >= gClient->mCurrentPriority) {
        float now = clock_elapsed();
        if (now >= mTimeout) {
            mTimeout = now + PEER_TIMEOUT;

            LOG_INFO("Peer '%" PRIu64 "' failed", mId);

            MPacketPeerFailed(
                { .lobbyId = gClient->mCurrentLobbyId, .peerId = mId }
            ).Send(*gClient->mConnection);
        }
    }
}

void Peer::Connect(const char* aSdp) {
    LOG_INFO("Receive SDP (%" PRIu64 ")", mId);
    int rc = juice_set_remote_description(mAgent, aSdp);
    WIIU_PEER_TRACE("coopnet peer: remote description rc=%d\n", rc);
#ifdef __WIIU__
    mJoinStage = rc ? "peer description rejected" : "checking routes";
#endif
    if (rc != 0) { return; }

    // Host candidates are gathered synchronously; STUN/TURN continues in the
    // background. Include the LAN endpoint in the answer so the offerer can
    // start checks without waiting for a separate candidate message. Worker
    // notifications are queued, so the answer still goes on the stream first.
    rc = juice_gather_candidates(mAgent);
    if (!mControlling) { SendSdp(); }
#ifdef __WIIU__
    if (rc) mJoinStage = "route gathering failed";
#endif
    WIIU_PEER_TRACE("coopnet peer: begin gathering rc=%d\n", rc);
}

void Peer::SendSdp() {
    if (juice_get_local_description(mAgent, mSdp, JUICE_MAX_SDP_STRING_LEN) != 0) return;
    LOG_INFO("\n\nSend SDP (%" PRIu64 "):\n------------------\n%s\n------------------\n", mId, mSdp);

    MPacketPeerSdp(
        { .lobbyId = gClient->mCurrentLobbyId, .userId = mId },
        { mSdp }
    ).Send(*gClient->mConnection);
}

bool Peer::Send(const uint8_t* aData, size_t aDataLength) {
    if (!mConnected) {
        LOG_INFO("Refusing send because not yet connected to (%" PRIu64 ")\n", mId);
        return false;
    }
    return juice_send(mAgent, (const char*)aData, aDataLength) == 0;
}

void Peer::Disconnect() {
    if (mAgent) {
        LOG_INFO("Peer disconnect %" PRIu64 "", mId);
        juice_destroy(mAgent);
        mAgent = nullptr;
        if (mTurnServers) {
            free(mTurnServers);
            mTurnServers = nullptr;
        }
        mConnected = false;
    }
}

void Peer::CandidateAdd(const char* aSdp) {
    LOG_INFO("\n\nReceive Candidate (%" PRIu64 "):\n------------------\n%s\n------------------\n", mId, aSdp);
    int rc = juice_add_remote_candidate(mAgent, aSdp);
#ifdef __WIIU__
    if (!rc) ++mRemoteCandidates;
#else
    (void)rc;
#endif
}

void Peer::CandidateDone() {
    LOG_INFO("Remote gathering done %" PRIu64 "", mId);
    int rc = juice_set_remote_gathering_done(mAgent);
    WIIU_PEER_TRACE("coopnet peer: remote gathering done rc=%d\n", rc);
}

void Peer::OnStateChanged(juice_state_t aState) {
    LOG_INFO("State change (%" PRIu64 "): %s", mId, juice_state_to_string(aState));
    WIIU_PEER_TRACE("coopnet peer: state %s\n", juice_state_to_string(aState));

    bool wasConnected = (mCurrentState == JUICE_STATE_CONNECTED) || (mCurrentState == JUICE_STATE_COMPLETED);
    bool wasDisconnected = (mCurrentState == JUICE_STATE_DISCONNECTED) || (mCurrentState == JUICE_STATE_FAILED);

    mConnected = (aState == JUICE_STATE_CONNECTED) || (aState == JUICE_STATE_COMPLETED);
    bool isDisconnected = (aState == JUICE_STATE_DISCONNECTED) || (aState == JUICE_STATE_FAILED);

    if (!wasConnected && mConnected) {
#ifdef __WIIU__
        mJoinStatusShown = true; // not an initial join stall anymore
#endif
        // Retrieve candidates
        char local[JUICE_MAX_CANDIDATE_SDP_STRING_LEN];
        char remote[JUICE_MAX_CANDIDATE_SDP_STRING_LEN];
        if (juice_get_selected_candidates(mAgent, local, JUICE_MAX_CANDIDATE_SDP_STRING_LEN, remote, JUICE_MAX_CANDIDATE_SDP_STRING_LEN) == 0) {
            LOG_INFO("Local candidate : %s\n", local);
            LOG_INFO("Remote candidate: %s\n", remote);

            if (strstr(local, "relay") != NULL || strstr(remote, "relay") != NULL) {
                LOG_INFO("Using TURN relay server");
            }
        }

        if (gCoopNetCallbacks.OnPeerConnected) {
            gCoopNetCallbacks.OnPeerConnected(mId);
        }
    }

    if (!wasDisconnected && isDisconnected) {
        if (gCoopNetCallbacks.OnPeerDisconnected) {
            gCoopNetCallbacks.OnPeerDisconnected(mId);
        }
    }

    mLastState = mCurrentState;
    mCurrentState = aState;
}

void Peer::OnCandidate(const char* aSdp) {
    WIIU_PEER_TRACE("coopnet peer: local candidate type=%s\n", strstr(aSdp, " typ relay") ? "relay" : strstr(aSdp, " typ srflx") ? "srflx" : strstr(aSdp, " typ host") ? "host" : "other");
    LOG_INFO("Candidate (%" PRIu64 "): %s", mId, aSdp);

    if (sForceRelay) {
        if (mControlling) {
            if (!strstr(aSdp, "relay")) {
                LOG_INFO("Rejecting non-relay!");
                return;
            }
        } else {
            if (!strstr(aSdp, "srflx")) {
                LOG_INFO("Rejecting non-srflx!");
                return;
            }
        }
    }

    LOG_INFO("\n\nSend Candidate (%" PRIu64 "):\n------------------\n%s\n------------------\n", mId, aSdp);
#ifdef __WIIU__
    ++mLocalCandidates;
#endif
    // Do not consume a second checklist slot for an exact SDP candidate line.
    const std::string line = std::string("\r\n") + aSdp + "\r\n";
    if (strstr(mSdp, line.c_str())) return;
    MPacketPeerCandidate(
        { .lobbyId = gClient->mCurrentLobbyId, .userId = mId },
        { aSdp }
    ).Send(*gClient->mConnection);
}

void Peer::OnGatheringDone() {
    // Older controlled peers only start gathering after this message. Do not
    // charge our own STUN/TURN gathering time against their connection window.
    // Extend once only; duplicate callbacks cannot keep an idle peer alive.
    if (mControlling && !mGatherCompletionSeen) {
        mGatherCompletionSeen = true;
        mTimeout = clock_elapsed() + PEER_TIMEOUT;
    }
    WIIU_PEER_TRACE("coopnet peer: local gathering done\n");
    LOG_INFO("Gathering done (%" PRIu64 ")", mId);
    MPacketPeerCandidateDone(
        { .lobbyId = gClient->mCurrentLobbyId, .userId = mId }
    ).Send(*gClient->mConnection);
}

void Peer::OnRecv(const uint8_t* aData, size_t aSize) {
    if (gCoopNetCallbacks.OnReceive) {
        gCoopNetCallbacks.OnReceive(mId, aData, (uint64_t)aSize);
    }
}
