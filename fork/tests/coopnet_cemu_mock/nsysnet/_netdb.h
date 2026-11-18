#pragma once
#include <netdb.h>
#define RPLWRAP(func) __rplwrap_##func
#ifdef __cplusplus
extern "C" {
#endif
struct hostent* __rplwrap_gethostbyname(const char*);
#ifdef __cplusplus
}
#endif
