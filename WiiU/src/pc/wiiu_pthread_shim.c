#ifdef TARGET_WII_U

#include <errno.h>
#include <stddef.h>
#include <unistd.h>

// This file used to hold the port's own pthread_* functions (mutexes over OSMutex, threads over
// OSThread), written for a compiler whose C library had the pthread types but not the functions.
// The C library of today's devkitPPC has the functions (mutexes, condition variables, threads,
// keys, once), and the Wii U library (wut) does the work under them: 128 KB of stack by default,
// priority 16, any core, which are the values the port's own functions used. So they are gone;
// they did not compile against today's types and would have stood in the C library's way.
//
// What is left is the one thing nothing else provides.

// The Wii U has no pipes. Nothing in the game should need one (libjuice was changed not to); this
// is here so that code that asks is told so instead of failing to link.
__attribute__((weak)) int pipe(int pipefd[2]) {
    (void) pipefd;
    errno = ENOSYS;
    return -1;
}

#endif // TARGET_WII_U
