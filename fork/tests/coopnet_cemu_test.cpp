#include <cassert>
#include <cstdio>
#include <cstring>
#include <netdb.h>
#include "coreinit/dynload.h"
#include "nsysnet/netconfig.h"
#include "socket.hpp"
#include "utils.hpp"

static int netconfMode = 0, initCalls = 0, closeCalls = 0, dnsMode = 0;
extern "C" int netconf_init() { ++initCalls; return netconfMode == 2 ? -1 : 0; }
extern "C" int netconf_close() { ++closeCalls; return 0; }
extern "C" int netconf_get_if_macaddr(NetConfInterfaceType type, NetConfMACAddr* m) {
    if (netconfMode == 1) return 0; // Cemu's unsupported HLE stub: no MAC written
    if (type == NET_CONF_INTERFACE_TYPE_ETHERNET) return -1;
    const uint8_t mac[] = { 1, 2, 3, 4, 5, 6 }; memcpy(m->MACAddr, mac, 6); return 0;
}
extern "C" struct hostent* __rplwrap_gethostbyname(const char*) {
    static char ip[] = { 1, 2, 3, 4 }, *list[] = { ip, nullptr }, *empty[] = { nullptr };
    static hostent entry = {};
    if (dnsMode == 0) return nullptr;
    entry.h_addrtype = dnsMode == 3 ? AF_INET6 : AF_INET;
    entry.h_length = dnsMode == 4 ? 2 : 4;
    entry.h_addr_list = dnsMode == 2 ? empty : list;
    return &entry;
}
int main() {
    uint64_t mac = 0x060504030201ULL;
    assert(SocketGetInfoBits(1, 123) == SocketAddHash(SOCKET_DEFAULT_INFO + mac));
    assert(initCalls == 1 && closeCalls == 1);
    netconfMode = 1;
    assert(SocketGetInfoBits(1, 123) == SocketAddHash(SOCKET_DEFAULT_INFO + 123));
    assert(SocketGetInfoBits(1, 456) == SocketAddHash(SOCKET_DEFAULT_INFO + 456));
    assert(initCalls == 3 && closeCalls == 3);
    netconfMode = 2;
    assert(SocketGetInfoBits(1, 456) == SocketAddHash(SOCKET_DEFAULT_INFO + 456));
    assert(initCalls == 4 && closeCalls == 3);
    in_addr_t addr = 0; in_addr expected = {};
    assert(!GetAddrFromDomain("", &addr));
    assert(!GetAddrFromDomain("example.invalid", &addr));
    dnsMode = 2; assert(!GetAddrFromDomain("example.invalid", &addr));
    dnsMode = 3; assert(!GetAddrFromDomain("example.invalid", &addr));
    dnsMode = 4; assert(!GetAddrFromDomain("example.invalid", &addr));
    dnsMode = 1; assert(GetAddrFromDomain("example.test", &addr));
    inet_pton(AF_INET, "1.2.3.4", &expected); assert(addr == expected.s_addr);
    dnsMode = 0; assert(GetAddrFromDomain("127.0.0.1", &addr));
    inet_pton(AF_INET, "127.0.0.1", &expected); assert(addr == expected.s_addr);
    assert(!GetAddrFromDomain("example.test", nullptr));
    puts("native and Cemu stub netconf, fallback identity, DNS failures and numeric IP: ok");
}
