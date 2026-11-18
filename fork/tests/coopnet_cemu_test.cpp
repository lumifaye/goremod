#include <cassert>
#include <cstdio>
#include <cstring>
#include <netdb.h>
#include "coreinit/dynload.h"
#include "nsysnet/netconfig.h"
#include "socket.hpp"
#include "utils.hpp"

static int loaderMode = 0, initCalls = 0, closeCalls = 0, releaseCalls = 0, dnsMode = 0;
extern "C" int netconf_init() { ++initCalls; return loaderMode == 3 ? -1 : 0; }
extern "C" int netconf_close() { ++closeCalls; return 0; }
extern "C" int netconf_get_if_macaddr(NetConfInterfaceType type, NetConfMACAddr* m) {
    if (type == NET_CONF_INTERFACE_TYPE_ETHERNET) return -1;
    const uint8_t mac[] = { 1, 2, 3, 4, 5, 6 }; memcpy(m->MACAddr, mac, 6); return 0;
}
extern "C" OSDynLoad_Error OSDynLoad_Acquire(const char*, OSDynLoad_Module* m) {
    if (loaderMode == 1) return OS_DYNLOAD_ERROR;
    *m = (void*)1; return OS_DYNLOAD_OK;
}
extern "C" OSDynLoad_Error OSDynLoad_FindExport(OSDynLoad_Module, OSDynLoad_ExportType, const char* n, void** out) {
    if (loaderMode == 2) { *out = nullptr; return OS_DYNLOAD_ERROR; }
    if (!strcmp(n,"netconf_init")) *out = reinterpret_cast<void*>(&netconf_init);
    else if (!strcmp(n,"netconf_close")) *out = reinterpret_cast<void*>(&netconf_close);
    else if (!strcmp(n,"netconf_get_if_macaddr")) *out = reinterpret_cast<void*>(&netconf_get_if_macaddr);
    else assert(false);
    return OS_DYNLOAD_OK;
}
extern "C" void OSDynLoad_Release(OSDynLoad_Module) { ++releaseCalls; }
extern "C" struct hostent* __wrap_gethostbyname(const char*) {
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
    assert(initCalls == 1 && closeCalls == 1 && releaseCalls == 1);
    loaderMode = 1;
    assert(SocketGetInfoBits(1, 123) == SocketAddHash(SOCKET_DEFAULT_INFO + 123));
    loaderMode = 2;
    assert(SocketGetInfoBits(1, 456) == SocketAddHash(SOCKET_DEFAULT_INFO + 456));
    assert(initCalls == 1 && closeCalls == 1 && releaseCalls == 2);
    loaderMode = 3;
    assert(SocketGetInfoBits(1, 456) == SocketAddHash(SOCKET_DEFAULT_INFO + 456));
    assert(initCalls == 2 && closeCalls == 1 && releaseCalls == 3);
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
    puts("native and missing netconf, fallback identity, DNS failures and numeric IP: ok");
}
