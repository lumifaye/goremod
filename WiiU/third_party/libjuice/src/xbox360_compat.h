/* xSDK's IPv4-only socket interface. libjuice's unused IPv6 types are compile-time placeholders.
 * This Source Code Form is subject to the Mozilla Public License, v. 2.0.
 * If a copy was not distributed with this file, see https://mozilla.org/MPL/2.0/. */
#ifndef JUICE_XBOX360_COMPAT_H
#define JUICE_XBOX360_COMPAT_H
#ifdef __XSDK__
#include <stdint.h>
#include <netinet/in.h>
#include <netdb.h>
#include <sys/socket.h>
#define JUICE_NO_IPV6
#define JUICE_NO_INTERRUPT
#ifndef HOST_NAME_MAX
#define HOST_NAME_MAX 256
#endif
#ifndef AF_INET6
#define AF_INET6 28
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
struct in6_addr { uint8_t s6_addr[16]; };
struct sockaddr_in6 { sa_family_t sin6_family; in_port_t sin6_port; uint32_t sin6_flowinfo; struct in6_addr sin6_addr; uint32_t sin6_scope_id; };
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
int juice_xbox360_getnameinfo(const struct sockaddr*, socklen_t, char*, socklen_t, char*, socklen_t, int);
#define getnameinfo juice_xbox360_getnameinfo
#endif
#endif
