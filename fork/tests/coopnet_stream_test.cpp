#include "client.hpp"
#include <cassert>
#include <cstring>
#include <string>
// Valid server notifications with an empty or non-NUL-terminated wire string.
static unsigned seen;
static void received(const char *host, uint32_t port) {
    assert(port == 123 && std::string(host) == (seen == 1 ? "" : "abc"));
    ++seen;
}
int main() {
    Connection connection(0);
    connection.mActive = true;
    gCoopNetCallbacks.OnLoadBalance = received;
    uint8_t full[] = {MPACKET_LOAD_BALANCE,0,4,0,5,0,123,0,0,0,3,0,'a','b','c'};
    uint8_t empty[] = {MPACKET_LOAD_BALANCE,0,4,0,2,0,123,0,0,0,0,0};
    uint8_t buf[64]; int64_t n=2;
    memcpy(buf,full,n); MPacket::Read(&connection,buf,&n,sizeof(buf)); assert(n==2 && !seen);
    memcpy(buf+n,full+n,sizeof(full)-n); memcpy(buf+sizeof(full),empty,sizeof(empty));
    memcpy(buf+sizeof(full)+sizeof(empty),full,5); n=sizeof(full)+sizeof(empty)+5;
    MPacket::Read(&connection,buf,&n,sizeof(buf)); assert(n==5 && seen==2);
    memcpy(buf+n,full+n,sizeof(full)-n); n=sizeof(full);
    MPacket::Read(&connection,buf,&n,sizeof(buf)); assert(n==0 && seen==3);
    gClient = new Client();
    gClient->mConnection = new Connection(1);
    gClient->mConnection->mActive = true;
    assert(coopnet_is_connected());
    gClient->mUpdating = true;
    assert(coopnet_shutdown() == COOPNET_OK && !coopnet_is_connected());
    assert(coopnet_update() == COOPNET_OK && gClient);
    assert(coopnet_begin("", 0, "", 0) == COOPNET_FAILED);
    gClient->mUpdating = false;
    gClient->mConnection->mActive = false;
    assert(coopnet_update() == COOPNET_OK && !gClient);
}
