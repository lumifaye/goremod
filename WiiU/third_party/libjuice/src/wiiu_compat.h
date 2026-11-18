/**
 * Wii U: what libjuice needs and the Wii U's network library (wut, nsysnet) does not have.
 * Not part of libjuice; added for the Wii U build of sm64coopdx. Included by socket.h.
 *
 * The Wii U has IPv4 only. Its headers have no IPv6 names at all, and its sockaddr_storage is 16
 * bytes (the size of sockaddr_in), which is also the only address size its socket calls are given
 * here. So:
 *   - the IPv6 names below exist only so that libjuice's IPv6 code compiles. No socket is ever
 *     AF_INET6 and no address of that family is ever made (JUICE_NO_IPV6 guards the places that
 *     would write one, since it would not fit in sockaddr_storage);
 *   - getaddrinfo, getnameinfo and freeaddrinfo are replaced by small IPv4 versions in
 *     wiiu_compat.c that use inet_pton, inet_ntop and gethostbyname;
 *   - there is no pipe() and no list of network interfaces: see conn_poll.c and udp.c.
 */

#ifndef JUICE_WIIU_COMPAT_H
#define JUICE_WIIU_COMPAT_H

#ifdef __WIIU__

#include <arpa/inet.h>
#include <netdb.h>
#include <netinet/in.h>
#include <stdint.h>
#include <sys/socket.h>

#define JUICE_NO_IPV6
#define JUICE_NO_INTERRUPT // conn_poll.c: no pipe and no loopback socket, a short poll instead
#define NO_IFADDRS
#ifndef NO_PMTUDISC
#define NO_PMTUDISC
#endif

#ifndef HOST_NAME_MAX
#define HOST_NAME_MAX 256
#endif

#ifndef AF_INET6
#define AF_INET6 28 // never given to the system
#endif
#ifndef IPPROTO_IPV6
#define IPPROTO_IPV6 41
#endif
#ifndef IPV6_V6ONLY
#define IPV6_V6ONLY 27
#endif
#ifndef INET6_ADDRSTRLEN
#define INET6_ADDRSTRLEN 46
#endif

#ifndef s6_addr
struct in6_addr {
	uint8_t s6_addr[16];
};
struct sockaddr_in6 {
	sa_family_t sin6_family;
	in_port_t sin6_port;
	uint32_t sin6_flowinfo;
	struct in6_addr sin6_addr;
	uint32_t sin6_scope_id;
};
#endif

#ifndef IN6_IS_ADDR_LOOPBACK
static inline int juice_wiiu_in6_is(const struct in6_addr *a, int zeros, uint8_t v10, uint8_t v11,
                                    int check15, uint8_t v15) {
	for (int i = 0; i < zeros; ++i)
		if (a->s6_addr[i] != 0)
			return 0;
	if (zeros == 10 && (a->s6_addr[10] != v10 || a->s6_addr[11] != v11))
		return 0;
	if (check15 && a->s6_addr[15] != v15)
		return 0;
	return 1;
}
#define IN6_IS_ADDR_LOOPBACK(a) juice_wiiu_in6_is((a), 15, 0, 0, 1, 1)
#define IN6_IS_ADDR_V4MAPPED(a) juice_wiiu_in6_is((a), 10, 0xFF, 0xFF, 0, 0)
#define IN6_IS_ADDR_LINKLOCAL(a) ((a)->s6_addr[0] == 0xFE && ((a)->s6_addr[1] & 0xC0) == 0x80)
#endif

#ifndef AI_NUMERICSERV
#define AI_NUMERICSERV 0x0400
#endif
#ifndef AI_NUMERICHOST
#define AI_NUMERICHOST 0x0004
#endif
#ifndef AI_PASSIVE
#define AI_PASSIVE 0x0001
#endif
#ifndef NI_NUMERICHOST
#define NI_NUMERICHOST 0x0002
#endif
#ifndef NI_NUMERICSERV
#define NI_NUMERICSERV 0x0008
#endif
#ifndef NI_DGRAM
#define NI_DGRAM 0x0010
#endif

int juice_wiiu_getaddrinfo(const char *node, const char *service, const struct addrinfo *hints,
                           struct addrinfo **res);
void juice_wiiu_freeaddrinfo(struct addrinfo *res);
int juice_wiiu_getnameinfo(const struct sockaddr *addr, socklen_t addrlen, char *host,
                           socklen_t hostlen, char *serv, socklen_t servlen, int flags);
// The address this console has on the network, in network byte order; 0 if it has none.
uint32_t juice_wiiu_local_address(void);

#define getaddrinfo juice_wiiu_getaddrinfo
#define freeaddrinfo juice_wiiu_freeaddrinfo
#define getnameinfo juice_wiiu_getnameinfo

#endif // __WIIU__

#endif // JUICE_WIIU_COMPAT_H
