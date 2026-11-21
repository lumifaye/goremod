#include "client.hpp"
#include "mpacket.hpp"
#include "utils.hpp"
#include "logging.hpp"
#ifdef __WIIU__
#include <coreinit/debug.h>
#define WIIU_COOPNET_TRACE(...) OSReport(__VA_ARGS__)
#elif defined(__XSDK__)
#define WIIU_COOPNET_TRACE(...) printf(__VA_ARGS__)
#else
#define WIIU_COOPNET_TRACE(...) ((void)0)
#endif

Client* gClient = NULL;

Client::~Client() {
    Disconnect();
    delete mConnection;
    for (auto &event : mEvents)
        if (event.type == PEER_EVENT_RECV) free((void*)event.data.recv.data);
}

bool Client::Begin(std::string aHost, uint32_t aPort, std::string aName, uint64_t aDestId)
{
    WIIU_COOPNET_TRACE("coopnet: Client::Begin start\n");
    mConnection = new Connection(0);

    // setup default stun server
    mStunServer.host = "stun.l.google.com";
    mStunServer.port = 19302;

    // setup a socket
    mConnection->mSocket = SocketInitialize(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if(mConnection->mSocket < 0)
    {
        WIIU_COOPNET_TRACE("coopnet: socket creation failed (errno=%d)\n", errno);
        LOG_ERROR("Socket failed");
        return false;
    }

    WIIU_COOPNET_TRACE("coopnet: socket ready; resolving server\n");

    // type of socket created
    mConnection->mAddress.sin_family = AF_INET;
    if (!GetAddrFromDomain(aHost, &mConnection->mAddress.sin_addr.s_addr)) {
        WIIU_COOPNET_TRACE("coopnet: server resolution failed\n");
        LOG_ERROR("Could not resolve CoopNet host: %s", aHost.c_str());
        SocketClose(mConnection->mSocket);
        mConnection->mSocket = -1;
        return false;
    }
    WIIU_COOPNET_TRACE("coopnet: server resolved; preparing socket\n");
    mConnection->mAddress.sin_port = htons(aPort);

#ifdef __XSDK__
    char ip[INET_ADDRSTRLEN] = {};
    inet_ntop(AF_INET, &mConnection->mAddress.sin_addr, ip, sizeof(ip));
    printf("coopnet: connecting to %s:%u\n", ip, (unsigned)aPort);
#endif
    SocketSetOptions(mConnection->mSocket);
    WIIU_COOPNET_TRACE("coopnet: socket options set\n");
    errno = 0;

    WIIU_COOPNET_TRACE("coopnet: connecting\n");
    int rc = connect(mConnection->mSocket, (struct sockaddr*) &mConnection->mAddress, sizeof(struct sockaddr_in));
    if (rc < 0) {
        rc = errno;
        if (rc == EINPROGRESS || rc == 0) {
            // Setup the timeout duration
            struct timeval timeout;
            timeout.tv_sec = 6;
            timeout.tv_usec = 0;

            // Setup the file descriptors to watch for write readiness
            fd_set writeSet;
            FD_ZERO(&writeSet);
            FD_SET(mConnection->mSocket, &writeSet);

            // Use select to wait for the socket to become writable or timeout
#ifdef __XSDK__
            fd_set errorSet = writeSet;
            int selectResult = select(mConnection->mSocket + 1, nullptr, &writeSet, &errorSet, &timeout);
#else
            int selectResult = select(mConnection->mSocket + 1, nullptr, &writeSet, nullptr, &timeout);
#endif
#ifdef __XSDK__
            if (selectResult > 0) {
                int error = 0;
                socklen_t length = sizeof(error);
                if (getsockopt(mConnection->mSocket, SOL_SOCKET, SO_ERROR, &error, &length) < 0 || error || FD_ISSET(mConnection->mSocket, &errorSet)) {
                    printf("coopnet: signaling connect failed (%d)\n", error ? error : errno);
                    SocketClose(mConnection->mSocket);
                    return false;
                }
            }
#endif
            if (selectResult == 0) {
                WIIU_COOPNET_TRACE("coopnet: TCP connect timed out after 6 seconds\n");
                LOG_ERROR("Connection timed out");
                SocketClose(mConnection->mSocket);
                return false;
            } else if (selectResult < 0) {
                WIIU_COOPNET_TRACE("coopnet: TCP select failed (errno=%d)\n", errno);
                LOG_ERROR("Error while waiting for connection");
                SocketClose(mConnection->mSocket);
                return false;
            }
        } else {
            // Other error occurred during connect
            WIIU_COOPNET_TRACE("coopnet: TCP connect failed (errno=%d)\n", rc);
            LOG_ERROR("Connect failed: %u", rc);
            SocketClose(mConnection->mSocket);
            return false;
        }
    }

    WIIU_COOPNET_TRACE("coopnet: initializing connection\n");
    mConnection->Begin(nullptr);
    WIIU_COOPNET_TRACE("coopnet: sending client info\n");

    uint64_t infoBits = SocketGetInfoBits(mConnection->mSocket, aDestId);
    WIIU_COOPNET_TRACE("coopnet: network identity ready\n");
    uint64_t fileHash = hashFile();
    WIIU_COOPNET_TRACE("coopnet: executable hash ready\n");
    MPacketInfo({
        .destId = aDestId,
        .infoBits = infoBits,
        .hash = fileHash,
    }, { aName }).Send(*mConnection);

    WIIU_COOPNET_TRACE("coopnet: client info sent\n");
    return true;
}

void Client::Update() {
    if (!mConnection) { return; }
    if (mUpdating) { return; }
    mUpdating = true;

    mConnection->Receive();
    if (mShutdown) { mUpdating = false; return; }
    mConnection->Update();
    if (mShutdown) { mUpdating = false; return; }

    // update peer
    for (auto& it : mPeers) {
        if (it.second) {
            it.second->Update();
        }
    }

    // copy events for processing
    std::vector<PeerEvent> mEventsCopy;
    {
        std::lock_guard<std::mutex> guard(mEventsMutex);
        mEventsCopy.swap(mEvents);
    }

    // process queued data on main thread
    {
        for (auto& it : mEventsCopy) {
            // A previous callback may have stopped the session. Still free
            // queued payloads, but do not deliver them to the old game.
            Peer* peer = mShutdown ? nullptr : PeerGet(it.peerId);

            switch (it.type) {
                case PEER_EVENT_CANDIDATE:
                    if (peer) peer->OnCandidate(it.candidate.c_str());
                    break;
                case PEER_EVENT_GATHERING_DONE:
                    if (peer) peer->OnGatheringDone();
                    break;
                case PEER_EVENT_STATE_CHANGED:
                    if (peer) {
                        peer->OnStateChanged(it.data.stateChanged.state);
                    }
                    break;
                case PEER_EVENT_RECV:
                    if (it.data.recv.data) {
                        if (peer) {
                            peer->OnRecv(it.data.recv.data, it.data.recv.dataSize);
                        }
                        free((void*)it.data.recv.data);
                        it.data.recv.data = nullptr;
                    }
                    break;
            }
        }
    }
    mUpdating = false;
}

void Client::Disconnect() {
    mShutdown = true;
    PeerEndAll();
    if (mConnection) {
        mConnection->Disconnect(true);
    }
}

void Client::PeerBegin(uint64_t aUserId, uint32_t aPriority) {
    if (PeerGet(aUserId)) return;
    mPeers[aUserId] = new Peer(this, aUserId, aPriority);
    LOG_INFO("Peer begin, count: %" PRIu64 "", (uint64_t)mPeers.size());
}

void Client::PeerEnd(uint64_t aUserId) {
    Peer* peer = PeerGet(aUserId);
    if (peer) {
        peer->Disconnect();
        mPeers.erase(peer->mId);
        delete peer;
    }
    LOG_INFO("Peer end, count: %" PRIu64 "", (uint64_t)mPeers.size());
}

void Client::PeerEndAll() {
    for (auto& it : mPeers) {
        Peer* peer = it.second;
        if (peer) {
            peer->Disconnect();
            delete peer;
        }
    }
    mPeers.clear();
    LOG_INFO("Peer end all, count: %" PRIu64 "", (uint64_t)mPeers.size());
}

Peer* Client::PeerGet(uint64_t aUserId) {
    auto it = mPeers.find(aUserId);
    return it == mPeers.end() ? nullptr : it->second;
}

bool Client::PeerSend(const uint8_t* aData, size_t aDataLength) {
    bool ret = true;
    for (auto& it : mPeers) {
        Peer* peer = it.second;
        if (!peer) { continue; }
        if (!peer->Send(aData, aDataLength)) {
            ret = false;
        }
    }
    return ret && (mPeers.size() > 0);
}

bool Client::PeerSendTo(uint64_t aPeerId, const uint8_t* aData, size_t aDataLength) {
    Peer* peer = PeerGet(aPeerId);
    if (!peer) { return false; }
    return peer->Send(aData, aDataLength);
}

void Client::LobbyCreate(std::string aGame, std::string aVersion, std::string aHostName, std::string aMode, uint16_t aMaxConnections, std::string aPassword, std::string aDescription) {
    MPacketLobbyCreate(
        { .maxConnections = aMaxConnections },
        { aGame.substr(0, 32), aVersion.substr(0, 32), aHostName.substr(0, 32), aMode.substr(0, 32), aPassword.substr(0, 64), aDescription.substr(0, 256) }
        ).Send(*mConnection);
}

void Client::LobbyUpdate(uint64_t aLobbyId, std::string aGame, std::string aVersion, std::string aHostName, std::string aMode, std::string aDescription) {
    MPacketLobbyUpdate(
        { .lobbyId = aLobbyId },
        { aGame.substr(0, 32), aVersion.substr(0, 32), aHostName.substr(0, 32), aMode.substr(0, 32), aDescription.substr(0, 256) }
        ).Send(*mConnection);
}

void Client::LobbyJoin(uint64_t aLobbyId, std::string aPassword) {
    MPacketLobbyJoin(
        { .lobbyId = aLobbyId },
        { aPassword.substr(0, 64) }
        ).Send(*mConnection);
}

void Client::LobbyLeave(uint64_t aLobbyId) {
    MPacketLobbyLeave(
        { .lobbyId = aLobbyId }
        ).Send(*mConnection);
}

void Client::LobbyListGet(std::string aGame, std::string aPassword) {
    MPacketLobbyListGet(
        {},
        { aGame.substr(0, 32), aPassword.substr(0, 64) }
        ).Send(*mConnection);
}
