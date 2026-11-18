/**
 * Wii U: see wiiu_compat.h. Not part of libjuice; added for the Wii U build of sm64coopdx.
 */

#ifdef __WIIU__

#include "socket.h" // brings wiiu_compat.h
#include "thread.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#undef getaddrinfo
#undef freeaddrinfo
#undef getnameinfo

// One result: the addrinfo and the address it points to, in one allocation.
typedef struct wiiu_ai {
	struct addrinfo ai;
	struct sockaddr_in sin;
} wiiu_ai_t;

static struct addrinfo *wiiu_ai_new(uint32_t s_addr, uint16_t port, const struct addrinfo *hints) {
	wiiu_ai_t *entry = calloc(1, sizeof(wiiu_ai_t));
	if (!entry)
		return NULL;

	entry->sin.sin_family = AF_INET;
	entry->sin.sin_port = htons(port);
	entry->sin.sin_addr.s_addr = s_addr;

	entry->ai.ai_family = AF_INET;
	entry->ai.ai_socktype = hints && hints->ai_socktype ? hints->ai_socktype : SOCK_DGRAM;
	entry->ai.ai_protocol = hints && hints->ai_protocol ? hints->ai_protocol : IPPROTO_UDP;
	entry->ai.ai_addrlen = sizeof(struct sockaddr_in);
	entry->ai.ai_addr = (struct sockaddr *)&entry->sin;
	return &entry->ai;
}

int juice_wiiu_getaddrinfo(const char *node, const char *service, const struct addrinfo *hints,
                           struct addrinfo **res) {
	if (!res || (!node && !service))
		return EAI_NONAME;

	*res = NULL;

	if (hints && hints->ai_family != AF_UNSPEC && hints->ai_family != AF_INET)
		return EAI_FAMILY;

	// The service is always a port number here
	long port = 0;
	if (service && *service) {
		char *end = NULL;
		port = strtol(service, &end, 10);
		if (!end || *end != '\0' || port < 0 || port > 0xFFFF)
			return EAI_SERVICE;
	}

	int flags = hints ? hints->ai_flags : 0;

	if (!node) {
		uint32_t any = (flags & AI_PASSIVE) ? htonl(INADDR_ANY) : htonl(INADDR_LOOPBACK);
		*res = wiiu_ai_new(any, (uint16_t)port, hints);
		return *res ? 0 : EAI_MEMORY;
	}

	struct in_addr numeric;
	if (inet_pton(AF_INET, node, &numeric) == 1) {
		*res = wiiu_ai_new(numeric.s_addr, (uint16_t)port, hints);
		return *res ? 0 : EAI_MEMORY;
	}

	if (flags & AI_NUMERICHOST)
		return EAI_NONAME;

	if (strcmp(node, "localhost") == 0) {
		*res = wiiu_ai_new(htonl(INADDR_LOOPBACK), (uint16_t)port, hints);
		return *res ? 0 : EAI_MEMORY;
	}

	// A name: gethostbyname keeps its answer in one shared place, so one caller at a time
	static mutex_t mutex = MUTEX_INITIALIZER;
	mutex_lock(&mutex);

	int ret = EAI_NONAME;
	struct hostent *he = gethostbyname(node);
	if (he && he->h_addrtype == AF_INET && he->h_length == 4 && he->h_addr_list) {
		struct addrinfo *first = NULL;
		struct addrinfo *last = NULL;
		for (int i = 0; he->h_addr_list[i] && i < 8; ++i) {
			uint32_t s_addr;
			memcpy(&s_addr, he->h_addr_list[i], 4);
			struct addrinfo *ai = wiiu_ai_new(s_addr, (uint16_t)port, hints);
			if (!ai)
				break;
			if (last)
				last->ai_next = ai;
			else
				first = ai;
			last = ai;
		}
		if (first) {
			*res = first;
			ret = 0;
		} else {
			ret = EAI_MEMORY;
		}
	}

	mutex_unlock(&mutex);
	return ret;
}

void juice_wiiu_freeaddrinfo(struct addrinfo *res) {
	while (res) {
		struct addrinfo *next = res->ai_next;
		free(res); // the addrinfo is the first member of its wiiu_ai_t
		res = next;
	}
}

int juice_wiiu_getnameinfo(const struct sockaddr *addr, socklen_t addrlen, char *host,
                           socklen_t hostlen, char *serv, socklen_t servlen, int flags) {
	(void)flags; // always numeric here
	if (!addr || addrlen < (socklen_t)sizeof(struct sockaddr_in) || addr->sa_family != AF_INET)
		return EAI_FAMILY;

	const struct sockaddr_in *sin = (const struct sockaddr_in *)addr;
	if (host && hostlen > 0) {
		if (!inet_ntop(AF_INET, &sin->sin_addr, host, hostlen))
			return EAI_OVERFLOW;
	}
	if (serv && servlen > 0) {
		int len = snprintf(serv, servlen, "%u", (unsigned int)ntohs(sin->sin_port));
		if (len < 0 || len >= (int)servlen)
			return EAI_OVERFLOW;
	}
	return 0;
}

uint32_t juice_wiiu_local_address(void) {
	// gethostid() is the address the console was given (ACGetAssignedAddress), as the number
	// 0xC0A80105 for 192.168.1.5. The Wii U is big-endian, so that is network byte order as it is.
	long id = gethostid();
	if (id == 0 || id == -1)
		return 0;
	return htonl((uint32_t)id);
}

#else

// Something has to be in this file on the other machines.
typedef int juice_wiiu_compat_unused_t;

#endif // __WIIU__
