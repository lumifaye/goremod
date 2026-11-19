/* Numeric IPv4 names for libjuice on xSDK. MPL-2.0: https://mozilla.org/MPL/2.0/. */
#ifdef __XSDK__
#include "xbox360_compat.h"
#include <arpa/inet.h>
#include <stdio.h>

int juice_xbox360_getnameinfo(const struct sockaddr *addr, socklen_t addrlen, char *host,
                              socklen_t hostlen, char *serv, socklen_t servlen, int flags) {
    if (!addr || addrlen < sizeof(struct sockaddr_in) || addr->sa_family != AF_INET) return EAI_FAMILY;
    if (flags & ~(NI_NUMERICHOST | NI_NUMERICSERV | NI_DGRAM)) return EAI_BADFLAGS;
    const struct sockaddr_in *in = (const struct sockaddr_in *)addr;
    if (host && (!hostlen || !inet_ntop(AF_INET, &in->sin_addr, host, hostlen))) return EAI_FAIL;
    if (serv) {
        if (!servlen) return EAI_FAIL;
        int n = snprintf(serv, servlen, "%u", (unsigned)ntohs(in->sin_port));
        if (n < 0 || (unsigned)n >= servlen) return EAI_FAIL;
    }
    return 0;
}
#endif
