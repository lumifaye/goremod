#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <netdb.h>
#include <arpa/inet.h>
#include <sys/socket.h>
int juice_wiiu_getaddrinfo(const char*, const char*, const struct addrinfo*, struct addrinfo**);
void juice_wiiu_freeaddrinfo(struct addrinfo*);
static int calls;
struct hostent* __rplwrap_gethostbyname(const char* name) {
    static char ip[] = { 8, 7, 6, 5 }, *list[] = { ip, NULL };
    static struct hostent h;
    ++calls;
    if (strcmp(name, "valid.test")) return NULL;
    memset(&h, 0, sizeof(h)); h.h_addrtype=AF_INET; h.h_length=4; h.h_addr_list=list; return &h;
}
struct hostent* gethostbyname(const char* name) { (void)name; assert(!"WUT wrapper must not be called"); return NULL; }
int main(void) {
    struct addrinfo *a = NULL; struct in_addr ip;
    assert(juice_wiiu_getaddrinfo("valid.test", "19302", NULL, &a) == 0 && a && calls == 1);
    inet_pton(AF_INET,"8.7.6.5",&ip);
    assert(((struct sockaddr_in*)a->ai_addr)->sin_addr.s_addr == ip.s_addr);
    assert(ntohs(((struct sockaddr_in*)a->ai_addr)->sin_port) == 19302);
    juice_wiiu_freeaddrinfo(a); a = NULL;
    assert(juice_wiiu_getaddrinfo("bad.test", "19302", NULL, &a) != 0 && a == NULL && calls == 2);
    assert(juice_wiiu_getaddrinfo("127.0.0.1", "19302", NULL, &a) == 0 && calls == 2);
    juice_wiiu_freeaddrinfo(a);
    puts("libjuice raw DNS, failure, numeric addresses: ok");
}
