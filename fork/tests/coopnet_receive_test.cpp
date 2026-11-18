#include <cassert>
#include <cstdio>
#include <cstring>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <unistd.h>
#include "connection.hpp"

CoopNetCallbacks gCoopNetCallbacks = {};
static int parsed = 0;
static int closed = 0;
static bool pretend_empty = false;
static char received[4] = {};

extern "C" ssize_t __real_recv(int fd, void* buf, size_t len, int flags);
extern "C" ssize_t __wrap_recv(int fd, void* buf, size_t len, int flags) {
    if (len == 0) { return 0; }
    return __real_recv(fd, buf, len, flags);
}

void SocketLimitBuffer(int fd, int64_t* amount) {
    int available = 0;
    assert(ioctl(fd, FIONREAD, &available) == 0);
    if (pretend_empty) { available = 0; }
    if (*amount > available) { *amount = available; }
}

int SocketClose(int fd) { return close(fd); }
void Lobby::Leave(Connection*) {}
void MPacket::Read(Connection*, uint8_t* data, int64_t* size, int64_t) {
    assert(*size > 0 && parsed + *size <= 3);
    memcpy(received + parsed, data, *size);
    parsed += (int)*size;
    *size = 0;
}

static void disconnected(bool intentional) {
    assert(!intentional);
    ++closed;
}

int main() {
    int fd[2];
    assert(socketpair(AF_UNIX, SOCK_STREAM, 0, fd) == 0);
    Connection c(1);
    c.mSocket = fd[0];
    c.mActive = true;
    gCoopNetCallbacks.OnDisconnected = disconnected;
    c.Receive();
    if (!c.mActive || closed != 0) {
        std::fputs("failed: empty receive disconnected the client\n", stderr);
        return 1;
    }
    assert(write(fd[1], "abc", 3) == 3);
    pretend_empty = true;
    c.Receive();
    assert(c.mActive && parsed == 3 && memcmp(received, "abc", 3) == 0 && closed == 0);
    pretend_empty = false;
    close(fd[1]);
    c.Receive();
    assert(!c.mActive && closed == 1);
    std::puts("idle, data and real disconnect: ok");
}
